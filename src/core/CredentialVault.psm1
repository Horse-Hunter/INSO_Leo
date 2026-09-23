Set-StrictMode -Version Latest

if ($PSVersionTable.PSEdition -eq 'Desktop') {
    Add-Type -AssemblyName System.Security
}

$script:VaultVersion = 1
$script:Entropy = [Text.Encoding]::UTF8.GetBytes('INSO_Leo.CredentialVault.v1')
$script:DefaultVaultPath = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'INSO_Leo\credential-vault.json'

function Resolve-InsoVaultPath {
    param([string]$VaultPath)
    if ([string]::IsNullOrWhiteSpace($VaultPath)) {
        return $script:DefaultVaultPath
    }
    return [IO.Path]::GetFullPath($VaultPath)
}

function Assert-WindowsVaultSupport {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'The INSO credential vault requires Windows DPAPI.'
    }
}

function New-EmptyVault {
    [pscustomobject]@{ version = $script:VaultVersion; entries = @() }
}

function Save-Vault {
    param(
        [Parameter(Mandatory)]$Vault,
        [Parameter(Mandatory)][string]$VaultPath
    )
    $directory = Split-Path -Parent $VaultPath
    if (-not (Test-Path -LiteralPath $directory)) {
        New-Item -ItemType Directory -Path $directory -Force | Out-Null
    }
    $json = $Vault | ConvertTo-Json -Depth 8
    $temporaryPath = "$VaultPath.$([Guid]::NewGuid().ToString('N')).tmp"
    try {
        [IO.File]::WriteAllText($temporaryPath, $json, [Text.UTF8Encoding]::new($false))
        Move-Item -LiteralPath $temporaryPath -Destination $VaultPath -Force
    }
    finally {
        if (Test-Path -LiteralPath $temporaryPath) {
            Remove-Item -LiteralPath $temporaryPath -Force
        }
    }
}

function Read-Vault {
    param([Parameter(Mandatory)][string]$VaultPath)
    if (-not (Test-Path -LiteralPath $VaultPath)) {
        throw "Credential vault does not exist: $VaultPath"
    }
    $json = [IO.File]::ReadAllText($VaultPath, [Text.UTF8Encoding]::new($false))
    $vault = ConvertFrom-Json -InputObject $json
    if ($vault.version -ne $script:VaultVersion) {
        throw "Unsupported credential vault version: $($vault.version)"
    }
    if ($null -eq $vault.entries) {
        $vault | Add-Member -NotePropertyName entries -NotePropertyValue @()
    }
    return $vault
}

function Protect-VaultPassword {
    param([Parameter(Mandatory)][Security.SecureString]$Password)
    $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Password)
    $plainBytes = $null
    try {
        $plainText = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
        $plainBytes = [Text.Encoding]::UTF8.GetBytes($plainText)
        $cipherBytes = [Security.Cryptography.ProtectedData]::Protect(
            $plainBytes,
            $script:Entropy,
            [Security.Cryptography.DataProtectionScope]::CurrentUser
        )
        return [Convert]::ToBase64String($cipherBytes)
    }
    finally {
        if ($null -ne $plainBytes) {
            [Array]::Clear($plainBytes, 0, $plainBytes.Length)
        }
        if ($bstr -ne [IntPtr]::Zero) {
            [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
        }
        Remove-Variable plainText -ErrorAction SilentlyContinue
    }
}

function Unprotect-VaultPassword {
    param([Parameter(Mandatory)][string]$PasswordCipher)
    $plainBytes = [Security.Cryptography.ProtectedData]::Unprotect(
        [Convert]::FromBase64String($PasswordCipher),
        $script:Entropy,
        [Security.Cryptography.DataProtectionScope]::CurrentUser
    )
    try {
        $plainText = [Text.Encoding]::UTF8.GetString($plainBytes)
        return ConvertTo-SecureString -String $plainText -AsPlainText -Force
    }
    finally {
        [Array]::Clear($plainBytes, 0, $plainBytes.Length)
        Remove-Variable plainText -ErrorAction SilentlyContinue
    }
}

function Assert-SiteId {
    param([Parameter(Mandatory)][string]$SiteId)
    if ($SiteId -notmatch '^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$') {
        throw 'SiteId must be 1-64 characters using letters, digits, dot, underscore, or hyphen.'
    }
}

function Assert-WebsiteUrl {
    param([string]$Url)
    if ([string]::IsNullOrWhiteSpace($Url)) {
        return
    }
    $parsed = $null
    if (-not [Uri]::TryCreate($Url, [UriKind]::Absolute, [ref]$parsed) -or $parsed.Scheme -notin @('http', 'https')) {
        throw 'Url must be an absolute HTTP or HTTPS URL.'
    }
}

function Initialize-InsoVault {
    [CmdletBinding()]
    param([string]$VaultPath)
    Assert-WindowsVaultSupport
    $resolvedPath = Resolve-InsoVaultPath $VaultPath
    if (-not (Test-Path -LiteralPath $resolvedPath)) {
        Save-Vault -Vault (New-EmptyVault) -VaultPath $resolvedPath
    }
    return $resolvedPath
}

function Get-InsoVaultPath {
    [CmdletBinding()]
    param([string]$VaultPath)
    Resolve-InsoVaultPath $VaultPath
}

function Get-InsoVaultEntries {
    [CmdletBinding()]
    param([string]$VaultPath)
    $resolvedPath = Initialize-InsoVault -VaultPath $VaultPath
    $vault = Read-Vault -VaultPath $resolvedPath
    foreach ($entry in @($vault.entries) | Sort-Object siteId) {
        $company = if ($entry.PSObject.Properties.Name -contains 'company') {
            [string]$entry.company
        } else {
            ''
        }
        [pscustomobject]@{
            SiteId = [string]$entry.siteId
            Url = [string]$entry.url
            Company = $company
            Username = [string]$entry.username
            Configured = -not [string]::IsNullOrWhiteSpace([string]$entry.passwordCipher)
            CreatedUtc = [string]$entry.createdUtc
            UpdatedUtc = [string]$entry.updatedUtc
        }
    }
}

function Add-InsoVaultSite {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SiteId,
        [Parameter(Mandatory)][string]$Url,
        [string]$VaultPath
    )
    Assert-SiteId $SiteId
    Assert-WebsiteUrl $Url
    $resolvedPath = Initialize-InsoVault -VaultPath $VaultPath
    $vault = Read-Vault -VaultPath $resolvedPath
    if (@($vault.entries | Where-Object siteId -EQ $SiteId).Count -gt 0) {
        return
    }
    $now = [DateTime]::UtcNow.ToString('o')
    $vault.entries = @($vault.entries) + [pscustomobject]@{
        siteId = $SiteId
        url = $Url
        company = ''
        username = ''
        passwordCipher = ''
        createdUtc = $now
        updatedUtc = $now
    }
    Save-Vault -Vault $vault -VaultPath $resolvedPath
}

function Set-InsoVaultCredential {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SiteId,
        [string]$Url,
        [string]$Company,
        [Parameter(Mandatory)][string]$Username,
        [Security.SecureString]$Password,
        [string]$VaultPath
    )
    Assert-SiteId $SiteId
    Assert-WebsiteUrl $Url
    if ([string]::IsNullOrWhiteSpace($Username)) {
        throw 'Username cannot be empty.'
    }
    $resolvedPath = Initialize-InsoVault -VaultPath $VaultPath
    $vault = Read-Vault -VaultPath $resolvedPath
    $entry = @($vault.entries | Where-Object siteId -EQ $SiteId) | Select-Object -First 1
    $now = [DateTime]::UtcNow.ToString('o')
    if ($null -eq $entry) {
        if ($null -eq $Password) {
            throw 'Password is required for a new credential.'
        }
        $entry = [pscustomobject]@{
            siteId = $SiteId
            url = if ($null -eq $Url) { '' } else { $Url }
            company = if ($null -eq $Company) { '' } else { $Company }
            username = $Username
            passwordCipher = Protect-VaultPassword $Password
            createdUtc = $now
            updatedUtc = $now
        }
        $vault.entries = @($vault.entries) + $entry
    }
    else {
        if ($null -ne $Url) {
            $entry.url = $Url
        }
        if ($PSBoundParameters.ContainsKey('Company')) {
            if ($entry.PSObject.Properties.Name -contains 'company') {
                $entry.company = $Company
            }
            else {
                $entry | Add-Member -NotePropertyName company -NotePropertyValue $Company
            }
        }
        $entry.username = $Username
        if ($null -ne $Password) {
            $entry.passwordCipher = Protect-VaultPassword $Password
        }
        if ([string]::IsNullOrWhiteSpace([string]$entry.passwordCipher)) {
            throw 'Password is required because this site has no configured credential.'
        }
        $entry.updatedUtc = $now
    }
    Save-Vault -Vault $vault -VaultPath $resolvedPath
}

function Get-InsoVaultCredential {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SiteId,
        [string]$VaultPath
    )
    Assert-SiteId $SiteId
    $resolvedPath = Initialize-InsoVault -VaultPath $VaultPath
    $vault = Read-Vault -VaultPath $resolvedPath
    $entry = @($vault.entries | Where-Object siteId -EQ $SiteId) | Select-Object -First 1
    if ($null -eq $entry) {
        throw "Credential site not found: $SiteId"
    }
    if ([string]::IsNullOrWhiteSpace([string]$entry.passwordCipher)) {
        throw "Credential is not configured for site: $SiteId"
    }
    $securePassword = Unprotect-VaultPassword -PasswordCipher $entry.passwordCipher
    return [Management.Automation.PSCredential]::new([string]$entry.username, $securePassword)
}

function Get-InsoVaultLogin {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SiteId,
        [string]$VaultPath
    )
    $entry = Get-InsoVaultEntries -VaultPath $VaultPath |
        Where-Object SiteId -EQ $SiteId |
        Select-Object -First 1
    if ($null -eq $entry) {
        throw "Credential site not found: $SiteId"
    }
    [pscustomobject]@{
        SiteId = $entry.SiteId
        Url = $entry.Url
        Company = $entry.Company
        Credential = Get-InsoVaultCredential -SiteId $SiteId -VaultPath $VaultPath
    }
}

function Remove-InsoVaultEntry {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$SiteId,
        [string]$VaultPath
    )
    Assert-SiteId $SiteId
    $resolvedPath = Initialize-InsoVault -VaultPath $VaultPath
    $vault = Read-Vault -VaultPath $resolvedPath
    $before = @($vault.entries).Count
    $vault.entries = @($vault.entries | Where-Object siteId -NE $SiteId)
    if (@($vault.entries).Count -eq $before) {
        throw "Credential site not found: $SiteId"
    }
    if ($PSCmdlet.ShouldProcess($SiteId, 'Remove credential vault entry')) {
        Save-Vault -Vault $vault -VaultPath $resolvedPath
    }
}

function Import-InsoVaultSites {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$SourcePath,
        [string]$VaultPath
    )
    $resolvedSource = [IO.Path]::GetFullPath($SourcePath)
    if (-not (Test-Path -LiteralPath $resolvedSource)) {
        throw "Site list does not exist: $resolvedSource"
    }
    $imported = 0
    foreach ($line in [IO.File]::ReadAllLines($resolvedSource, [Text.UTF8Encoding]::new($false))) {
        if ([string]::IsNullOrWhiteSpace($line)) {
            continue
        }
        $parts = @($line.Trim() -split [regex]::Escape([string][char]0xFF0C))
        if ($parts.Count -notin @(1, 3, 4)) {
            throw 'The site list contains an unsupported record shape.'
        }
        $urlText = $parts[0].Trim()
        $uri = $null
        if (-not [Uri]::TryCreate($urlText, [UriKind]::Absolute, [ref]$uri) -or $uri.Scheme -notin @('http', 'https')) {
            throw 'The site list contains a line that is not an absolute HTTP or HTTPS URL.'
        }
        $existingEntries = @(Get-InsoVaultEntries -VaultPath $VaultPath)
        if ($uri.AbsoluteUri -in @($existingEntries | ForEach-Object { $_.Url })) {
            continue
        }
        $baseId = (($uri.DnsSafeHost.ToLowerInvariant() -replace '^www\.', '') -replace '[^a-z0-9._-]', '-')
        $siteId = $baseId
        $suffix = 2
        $existingIds = @(
            $existingEntries | ForEach-Object { $_.SiteId }
        )
        while ($siteId -in $existingIds) {
            $siteId = "$baseId-$suffix"
            $suffix++
        }
        if ($parts.Count -eq 1) {
            Add-InsoVaultSite -SiteId $siteId -Url $uri.AbsoluteUri -VaultPath $VaultPath
        }
        else {
            $company = if ($parts.Count -eq 4) { $parts[1].Trim() } else { '' }
            $username = $parts[$parts.Count - 2].Trim()
            $password = ConvertTo-SecureString -String $parts[$parts.Count - 1] -AsPlainText -Force
            Set-InsoVaultCredential -SiteId $siteId -Url $uri.AbsoluteUri -Company $company -Username $username -Password $password -VaultPath $VaultPath
        }
        $imported++
    }
    return $imported
}

Export-ModuleMember -Function @(
    'Initialize-InsoVault',
    'Get-InsoVaultPath',
    'Get-InsoVaultEntries',
    'Add-InsoVaultSite',
    'Set-InsoVaultCredential',
    'Get-InsoVaultCredential',
    'Get-InsoVaultLogin',
    'Remove-InsoVaultEntry',
    'Import-InsoVaultSites'
)
