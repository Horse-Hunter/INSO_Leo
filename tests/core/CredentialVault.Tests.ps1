Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$repositoryRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$modulePath = Join-Path $repositoryRoot 'src\core\CredentialVault.psm1'
Import-Module $modulePath -Force

$testRoot = Join-Path ([IO.Path]::GetTempPath()) "inso-vault-test-$([Guid]::NewGuid().ToString('N'))"
$vaultPath = Join-Path $testRoot 'vault.json'
$siteListPath = Join-Path $testRoot 'sites.txt'
$dummySecret = 'dummy-secret-for-tests-only'

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        throw "Assertion failed: $Message"
    }
}

try {
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
    [IO.File]::WriteAllLines(
        $siteListPath,
        @(
            'https://example.com/',
            'https://example.org/login',
            "https://portal.example.net/$([char]0xFF0C)Example Co$([char]0xFF0C)import-user$([char]0xFF0C)import-password"
        )
    )

    $initialized = Initialize-InsoVault -VaultPath $vaultPath
    Assert-True ($initialized -eq $vaultPath) 'initialize returns the requested path'
    Assert-True (Test-Path -LiteralPath $vaultPath) 'vault file is created'

    $imported = Import-InsoVaultSites -SourcePath $siteListPath -VaultPath $vaultPath
    Assert-True ($imported -eq 3) 'three site records are imported'
    $entries = @(Get-InsoVaultEntries -VaultPath $vaultPath)
    Assert-True ($entries.Count -eq 3) 'three metadata entries exist'
    Assert-True (-not $entries[0].Configured) 'imported site has no credential yet'
    $importedLogin = Get-InsoVaultLogin -SiteId 'portal.example.net' -VaultPath $vaultPath
    Assert-True ($importedLogin.Company -eq 'Example Co') 'company is parsed from a delimited record'
    Assert-True ($importedLogin.Credential.UserName -eq 'import-user') 'username is parsed from a delimited record'
    Assert-True ($importedLogin.Credential.GetNetworkCredential().Password -eq 'import-password') 'imported password is encrypted and retrievable'
    $reimported = Import-InsoVaultSites -SourcePath $siteListPath -VaultPath $vaultPath
    Assert-True ($reimported -eq 0) 'repeated import is idempotent'

    $secure = ConvertTo-SecureString -String $dummySecret -AsPlainText -Force
    Set-InsoVaultCredential -SiteId 'example.com' -Url 'https://example.com/' -Company 'Example Trading' -Username 'dummy-user' -Password $secure -VaultPath $vaultPath
    $credential = Get-InsoVaultCredential -SiteId 'example.com' -VaultPath $vaultPath
    Assert-True ($credential.UserName -eq 'dummy-user') 'username round-trips'
    Assert-True ($credential.GetNetworkCredential().Password -eq $dummySecret) 'password round-trips through DPAPI'
    $login = Get-InsoVaultLogin -SiteId 'example.com' -VaultPath $vaultPath
    Assert-True ($login.Company -eq 'Example Trading') 'company round-trips'
    Assert-True ($login.Credential.UserName -eq 'dummy-user') 'complete login returns credential'

    $rawVault = Get-Content -LiteralPath $vaultPath -Raw
    Assert-True (-not $rawVault.Contains($dummySecret)) 'vault JSON does not contain plaintext password'

    $updatedSecure = ConvertTo-SecureString -String 'updated-dummy-secret' -AsPlainText -Force
    Set-InsoVaultCredential -SiteId 'example.com' -Url 'https://example.com/sign-in' -Company 'Updated Trading' -Username 'updated-user' -Password $updatedSecure -VaultPath $vaultPath
    $updated = Get-InsoVaultCredential -SiteId 'example.com' -VaultPath $vaultPath
    Assert-True ($updated.UserName -eq 'updated-user') 'credential update changes username'
    Assert-True ($updated.GetNetworkCredential().Password -eq 'updated-dummy-secret') 'credential update changes password'
    Assert-True ((Get-InsoVaultLogin -SiteId 'example.com' -VaultPath $vaultPath).Company -eq 'Updated Trading') 'credential update changes company'

    Remove-InsoVaultEntry -SiteId 'example.org' -VaultPath $vaultPath -Confirm:$false
    Assert-True (@(Get-InsoVaultEntries -VaultPath $vaultPath).Count -eq 2) 'entry deletion works'

    Write-Output 'PASS: CredentialVault tests completed successfully.'
}
finally {
    if (Test-Path -LiteralPath $testRoot) {
        Remove-Item -LiteralPath $testRoot -Recurse -Force
    }
}
