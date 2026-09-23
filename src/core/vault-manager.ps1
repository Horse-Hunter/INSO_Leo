[CmdletBinding()]
param(
    [string]$VaultPath,
    [switch]$SmokeTest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Import-Module (Join-Path $PSScriptRoot 'CredentialVault.psm1') -Force
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[Windows.Forms.Application]::EnableVisualStyles()
$resolvedVaultPath = Initialize-InsoVault -VaultPath $VaultPath

function Show-ErrorMessage {
    param([string]$Message)
    [Windows.Forms.MessageBox]::Show(
        $Message,
        'Credential Vault',
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
}

function Show-CredentialEditor {
    param($ExistingEntry)

    $isEdit = $null -ne $ExistingEntry
    $dialog = [Windows.Forms.Form]::new()
    $dialog.Text = if ($isEdit) { 'Edit credential' } else { 'Add credential' }
    $dialog.StartPosition = [Windows.Forms.FormStartPosition]::CenterParent
    $dialog.ClientSize = [Drawing.Size]::new(520, 355)
    $dialog.FormBorderStyle = [Windows.Forms.FormBorderStyle]::FixedDialog
    $dialog.MaximizeBox = $false
    $dialog.MinimizeBox = $false

    $labels = @('Site ID', 'Website URL', 'Company', 'Username', 'Password')
    $inputs = @()
    for ($index = 0; $index -lt $labels.Count; $index++) {
        $label = [Windows.Forms.Label]::new()
        $label.Text = $labels[$index]
        $label.Location = [Drawing.Point]::new(20, 24 + (55 * $index))
        $label.Size = [Drawing.Size]::new(100, 24)
        $dialog.Controls.Add($label)

        $input = [Windows.Forms.TextBox]::new()
        $input.Location = [Drawing.Point]::new(125, 20 + (55 * $index))
        $input.Size = [Drawing.Size]::new(370, 27)
        $dialog.Controls.Add($input)
        $inputs += $input
    }

    $siteIdInput, $urlInput, $companyInput, $usernameInput, $passwordInput = $inputs
    $passwordInput.UseSystemPasswordChar = $true
    if ($isEdit) {
        $siteIdInput.Text = $ExistingEntry.SiteId
        $siteIdInput.ReadOnly = $true
        $urlInput.Text = $ExistingEntry.Url
        $companyInput.Text = $ExistingEntry.Company
        $usernameInput.Text = $ExistingEntry.Username
    }

    $passwordHint = [Windows.Forms.Label]::new()
    $passwordHint.Text = if ($isEdit -and $ExistingEntry.Configured) {
        'Leave blank to keep the current password.'
    } else {
        'A password is required before automation can use this entry.'
    }
    $passwordHint.Location = [Drawing.Point]::new(125, 296)
    $passwordHint.Size = [Drawing.Size]::new(370, 20)
    $passwordHint.ForeColor = [Drawing.Color]::DimGray
    $dialog.Controls.Add($passwordHint)

    $saveButton = [Windows.Forms.Button]::new()
    $saveButton.Text = 'Save'
    $saveButton.Location = [Drawing.Point]::new(325, 320)
    $saveButton.Size = [Drawing.Size]::new(80, 30)
    $dialog.Controls.Add($saveButton)

    $cancelButton = [Windows.Forms.Button]::new()
    $cancelButton.Text = 'Cancel'
    $cancelButton.Location = [Drawing.Point]::new(415, 320)
    $cancelButton.Size = [Drawing.Size]::new(80, 30)
    $cancelButton.DialogResult = [Windows.Forms.DialogResult]::Cancel
    $dialog.Controls.Add($cancelButton)
    $dialog.CancelButton = $cancelButton

    $saveButton.Add_Click({
        try {
            $arguments = @{
                SiteId = $siteIdInput.Text.Trim()
                Url = $urlInput.Text.Trim()
                Company = $companyInput.Text.Trim()
                Username = $usernameInput.Text.Trim()
                VaultPath = $resolvedVaultPath
            }
            if (-not [string]::IsNullOrEmpty($passwordInput.Text)) {
                $arguments.Password = ConvertTo-SecureString -String $passwordInput.Text -AsPlainText -Force
            }
            Set-InsoVaultCredential @arguments
            $passwordInput.Clear()
            $dialog.DialogResult = [Windows.Forms.DialogResult]::OK
            $dialog.Close()
        }
        catch {
            $passwordInput.Clear()
            Show-ErrorMessage $_.Exception.Message
        }
    })

    $dialog.AcceptButton = $saveButton
    try {
        return $dialog.ShowDialog($form)
    }
    finally {
        $passwordInput.Clear()
        $dialog.Dispose()
    }
}

$form = [Windows.Forms.Form]::new()
$form.Text = 'INSO Leo Credential Vault'
$form.StartPosition = [Windows.Forms.FormStartPosition]::CenterScreen
$form.ClientSize = [Drawing.Size]::new(900, 520)
$form.MinimumSize = [Drawing.Size]::new(760, 430)

$title = [Windows.Forms.Label]::new()
$title.Text = 'Local website credentials'
$title.Font = [Drawing.Font]::new('Segoe UI', 14, [Drawing.FontStyle]::Bold)
$title.Location = [Drawing.Point]::new(18, 15)
$title.Size = [Drawing.Size]::new(400, 32)
$form.Controls.Add($title)

$subtitle = [Windows.Forms.Label]::new()
$subtitle.Text = 'Passwords are encrypted with Windows DPAPI for the current Windows user.'
$subtitle.Location = [Drawing.Point]::new(20, 50)
$subtitle.Size = [Drawing.Size]::new(700, 24)
$subtitle.ForeColor = [Drawing.Color]::DimGray
$form.Controls.Add($subtitle)

$grid = [Windows.Forms.DataGridView]::new()
$grid.Location = [Drawing.Point]::new(20, 82)
$grid.Size = [Drawing.Size]::new(860, 350)
$grid.Anchor = [Windows.Forms.AnchorStyles]::Top -bor
    [Windows.Forms.AnchorStyles]::Bottom -bor
    [Windows.Forms.AnchorStyles]::Left -bor
    [Windows.Forms.AnchorStyles]::Right
$grid.ReadOnly = $true
$grid.AllowUserToAddRows = $false
$grid.AllowUserToDeleteRows = $false
$grid.AllowUserToResizeRows = $false
$grid.AutoSizeColumnsMode = [Windows.Forms.DataGridViewAutoSizeColumnsMode]::Fill
$grid.SelectionMode = [Windows.Forms.DataGridViewSelectionMode]::FullRowSelect
$grid.MultiSelect = $false
$grid.RowHeadersVisible = $false
$form.Controls.Add($grid)

$status = [Windows.Forms.Label]::new()
$status.Location = [Drawing.Point]::new(20, 445)
$status.Size = [Drawing.Size]::new(540, 45)
$status.Anchor = [Windows.Forms.AnchorStyles]::Bottom -bor [Windows.Forms.AnchorStyles]::Left
$status.ForeColor = [Drawing.Color]::DimGray
$status.Text = "Vault: $resolvedVaultPath"
$form.Controls.Add($status)

$addButton = [Windows.Forms.Button]::new()
$addButton.Text = 'Add'
$addButton.Location = [Drawing.Point]::new(575, 450)
$addButton.Size = [Drawing.Size]::new(90, 32)
$addButton.Anchor = [Windows.Forms.AnchorStyles]::Bottom -bor [Windows.Forms.AnchorStyles]::Right
$form.Controls.Add($addButton)

$editButton = [Windows.Forms.Button]::new()
$editButton.Text = 'Edit'
$editButton.Location = [Drawing.Point]::new(675, 450)
$editButton.Size = [Drawing.Size]::new(90, 32)
$editButton.Anchor = [Windows.Forms.AnchorStyles]::Bottom -bor [Windows.Forms.AnchorStyles]::Right
$form.Controls.Add($editButton)

$deleteButton = [Windows.Forms.Button]::new()
$deleteButton.Text = 'Delete'
$deleteButton.Location = [Drawing.Point]::new(775, 450)
$deleteButton.Size = [Drawing.Size]::new(90, 32)
$deleteButton.Anchor = [Windows.Forms.AnchorStyles]::Bottom -bor [Windows.Forms.AnchorStyles]::Right
$form.Controls.Add($deleteButton)

function Refresh-VaultGrid {
    $table = [Data.DataTable]::new()
    [void]$table.Columns.Add('Site ID')
    [void]$table.Columns.Add('Website URL')
    [void]$table.Columns.Add('Company')
    [void]$table.Columns.Add('Username')
    [void]$table.Columns.Add('Configured')
    [void]$table.Columns.Add('Updated (UTC)')
    foreach ($entry in Get-InsoVaultEntries -VaultPath $resolvedVaultPath) {
        [void]$table.Rows.Add(
            $entry.SiteId,
            $entry.Url,
            $entry.Company,
            $entry.Username,
            $(if ($entry.Configured) { 'Yes' } else { 'No' }),
            $entry.UpdatedUtc
        )
    }
    $grid.DataSource = $table
    if ($grid.Columns.Count -ge 6) {
        $grid.Columns[0].FillWeight = 70
        $grid.Columns[1].FillWeight = 150
        $grid.Columns[2].FillWeight = 90
        $grid.Columns[3].FillWeight = 90
        $grid.Columns[4].FillWeight = 55
        $grid.Columns[5].FillWeight = 100
    }
}

function Get-SelectedVaultEntry {
    if ($grid.SelectedRows.Count -eq 0) {
        return $null
    }
    $siteId = [string]$grid.SelectedRows[0].Cells['Site ID'].Value
    return Get-InsoVaultEntries -VaultPath $resolvedVaultPath |
        Where-Object SiteId -EQ $siteId |
        Select-Object -First 1
}

$addButton.Add_Click({
    if ((Show-CredentialEditor -ExistingEntry $null) -eq [Windows.Forms.DialogResult]::OK) {
        Refresh-VaultGrid
    }
})

$editButton.Add_Click({
    $entry = Get-SelectedVaultEntry
    if ($null -eq $entry) {
        Show-ErrorMessage 'Select an entry to edit.'
        return
    }
    if ((Show-CredentialEditor -ExistingEntry $entry) -eq [Windows.Forms.DialogResult]::OK) {
        Refresh-VaultGrid
    }
})

$grid.Add_CellDoubleClick({
    if ($_.RowIndex -ge 0) {
        $editButton.PerformClick()
    }
})

$deleteButton.Add_Click({
    $entry = Get-SelectedVaultEntry
    if ($null -eq $entry) {
        Show-ErrorMessage 'Select an entry to delete.'
        return
    }
    $answer = [Windows.Forms.MessageBox]::Show(
        "Delete credential entry '$($entry.SiteId)'?",
        'Confirm deletion',
        [Windows.Forms.MessageBoxButtons]::YesNo,
        [Windows.Forms.MessageBoxIcon]::Warning
    )
    if ($answer -eq [Windows.Forms.DialogResult]::Yes) {
        try {
            Remove-InsoVaultEntry -SiteId $entry.SiteId -VaultPath $resolvedVaultPath -Confirm:$false
            Refresh-VaultGrid
        }
        catch {
            Show-ErrorMessage $_.Exception.Message
        }
    }
})

Refresh-VaultGrid
if ($SmokeTest) {
    Write-Output 'PASS: Credential vault manager constructed successfully.'
}
else {
    [void]$form.ShowDialog()
}
$form.Dispose()
