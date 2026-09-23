[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('init', 'path', 'list', 'add', 'edit', 'remove', 'import-sites')]
    [string]$Command = 'list',
    [string]$SiteId,
    [string]$Url,
    [string]$SourcePath,
    [string]$VaultPath,
    [switch]$Force
)

Set-StrictMode -Version Latest
Import-Module (Join-Path $PSScriptRoot 'CredentialVault.psm1') -Force

switch ($Command) {
    'init' {
        Initialize-InsoVault -VaultPath $VaultPath
    }
    'path' {
        Get-InsoVaultPath -VaultPath $VaultPath
    }
    'list' {
        Get-InsoVaultEntries -VaultPath $VaultPath |
            Format-Table SiteId, Url, Username, Configured, UpdatedUtc -AutoSize
    }
    { $_ -in @('add', 'edit') } {
        if ([string]::IsNullOrWhiteSpace($SiteId)) {
            $SiteId = Read-Host 'Site ID (letters, digits, dot, underscore, hyphen)'
        }
        if ($null -eq $Url) {
            $Url = Read-Host 'Website URL'
        }
        $username = Read-Host 'Username'
        $company = Read-Host 'Company (optional)'
        $password = Read-Host 'Password (hidden)' -AsSecureString
        Set-InsoVaultCredential -SiteId $SiteId -Url $Url -Company $company -Username $username -Password $password -VaultPath $VaultPath
        Write-Output "Credential saved for $SiteId."
    }
    'remove' {
        if ([string]::IsNullOrWhiteSpace($SiteId)) {
            throw 'SiteId is required for remove.'
        }
        if (-not $Force) {
            $answer = Read-Host "Type DELETE to remove $SiteId"
            if ($answer -cne 'DELETE') {
                Write-Output 'Cancelled.'
                break
            }
        }
        Remove-InsoVaultEntry -SiteId $SiteId -VaultPath $VaultPath -Confirm:$false
        Write-Output "Credential removed for $SiteId."
    }
    'import-sites' {
        if ([string]::IsNullOrWhiteSpace($SourcePath)) {
            throw 'SourcePath is required for import-sites.'
        }
        $count = Import-InsoVaultSites -SourcePath $SourcePath -VaultPath $VaultPath
        Write-Output "Imported $count website entries."
    }
}
