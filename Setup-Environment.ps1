# PowerShell script to install 32-bit Python, pip, and create a virtual environment

$pythonVersion = "3.9.13"  # Change as needed
$installDir = "python-$pythonVersion-32"
$venvName = "$((Get-Item -Path ".\").Name)_env"
$pythonExe = "$installDir\python.exe"

function Test-Command {
    param($command)
    try {
        & $command --version | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

# 1. Download & Extract Python
Write-Host "`nDownloading Python $pythonVersion 32-bit (Embedded)..." -ForegroundColor Yellow
$embeddedUrl = "https://www.python.org/ftp/python/$pythonVersion/python-$pythonVersion-embed-win32.zip"
$zipFile = "python-embedded.zip"

if (-not (Test-Path $installDir)) {
    try {
        Invoke-WebRequest -Uri $embeddedUrl -OutFile $zipFile -ErrorAction Stop
        Write-Host "Extracting Python..." -ForegroundColor Yellow
        Expand-Archive -Path $zipFile -DestinationPath $installDir -Force
        Remove-Item $zipFile -Force
    }
    catch {
        Write-Error "Python download or extraction failed: $_"
        exit 1
    }
}

# 1.5. Enable site packages in the embedded Python
# The embedded distribution comes with a python39._pth file that disables 'import site'.
# Removing the '#' before 'import site' allows pip and other modules to work correctly.
$pthFile = Join-Path $installDir "python39._pth"
if (Test-Path $pthFile) {
    (Get-Content $pthFile) | ForEach-Object {
        if ($_ -match "^\s*#\s*import\s+site") { "import site" } else { $_ }
    } | Set-Content $pthFile -Encoding ASCII
    Write-Host "Modified $pthFile to enable site packages." -ForegroundColor Green
}

# 2. Verify Python Installation
Write-Host "`nVerifying Python installation..." -ForegroundColor Yellow
if (-not (Test-Path $pythonExe)) {
    Write-Error "Python executable not found!"
    exit 1
}

# 3. Install pip manually
Write-Host "`nInstalling pip..." -ForegroundColor Yellow
$getPipUrl = "https://bootstrap.pypa.io/get-pip.py"
$getPipPath = "$installDir\get-pip.py"

try {
    Invoke-WebRequest -Uri $getPipUrl -OutFile $getPipPath -ErrorAction Stop
    & $pythonExe $getPipPath
    Remove-Item $getPipPath -Force
}
catch {
    Write-Error "pip installation failed: $_"
    exit 1
}

# 4. Add Python and Scripts directory to PATH for this session
$env:Path = "$installDir;$installDir\Scripts;$env:Path"

# 5. Verify pip installation
Write-Host "`nVerifying pip installation..." -ForegroundColor Yellow
Start-Sleep -Seconds 1  # Allow time for PATH update
if (-not (Test-Command "pip")) {
    Write-Error "pip is not installed correctly."
    exit 1
}

# 6. Install virtualenv (along with pip upgrade, setuptools and wheel)
Write-Host "`nInstalling virtualenv..." -ForegroundColor Yellow
try {
    & $pythonExe -m pip install --upgrade pip setuptools wheel virtualenv
}
catch {
    Write-Error "Failed to install virtualenv: $_"
    exit 1
}

# 7. Verify virtualenv installation by checking its version
Write-Host "`nVerifying virtualenv installation..." -ForegroundColor Yellow
try {
    & $pythonExe -m virtualenv --version | Out-Null
}
catch {
    Write-Error "virtualenv is not installed correctly."
    exit 1
}

# 8. Create Virtual Environment
Write-Host "`nCreating virtual environment '$venvName'..." -ForegroundColor Yellow

# Remove existing virtual environment if it exists
if (Test-Path $venvName) {
    Write-Host "Removing existing virtual environment..." -ForegroundColor Yellow
    try {
        Remove-Item -Recurse -Force -Path $venvName -ErrorAction Stop
        Write-Host "Existing virtual environment removed." -ForegroundColor Green
    }
    catch {
        Write-Error "Failed to remove existing virtual environment: $_"
        exit 1
    }
}

try {
    & $pythonExe -m virtualenv $venvName
    if (-not (Test-Path "$venvName\Scripts\activate")) {
        throw "Virtual environment creation failed."
    }
}
catch {
    Write-Error "Virtual environment creation failed: $_"
    exit 1
}

Write-Host "`nVirtual environment created successfully." -ForegroundColor Green

# 9. Upgrade pip inside virtualenv
Write-Host "`nUpgrading pip in virtual environment..." -ForegroundColor Yellow
$venvPython = "$venvName\Scripts\python.exe"
try {
    & $venvPython -m pip install --upgrade pip
}
catch {
    Write-Warning "Failed to upgrade pip in virtual environment. This might not be critical."
}

# 10. Install requirements.txt inside the virtual environment
Write-Host "`nInstalling packages from requirements.txt (if found) inside the virtual environment..." -ForegroundColor Yellow
$requirementsFile = "requirements.txt"
if (Test-Path $requirementsFile) {
    try {
        & "$venvName\Scripts\pip.exe" install -r $requirementsFile
        Write-Host "Packages installed in the virtual environment." -ForegroundColor Green
    }
    catch {
        Write-Error "Package installation from requirements.txt failed: $_"
    }
} else {
    Write-Warning "requirements.txt not found. Skipping."
}

# 11. Activation Instructions
Write-Host "`nVirtual environment setup complete!" -ForegroundColor Green
Write-Host "To activate: .\$venvName\Scripts\Activate.ps1" -ForegroundColor Cyan
Write-Host "To deactivate: deactivate" -ForegroundColor Cyan

# 12. Update .gitignore
$gitignorePath = ".\\.gitignore"
$gitignoreContent = @"
$installDir/
$venvName/
python-embedded.zip
"@

if (Test-Path $gitignorePath) {
    if (!(Get-Content $gitignorePath -Raw).Contains($gitignoreContent)) {
        Add-Content -Path $gitignorePath -Value "`n$gitignoreContent"
        Write-Host ".gitignore updated." -ForegroundColor Green
    }
} else {
    Set-Content -Path $gitignorePath -Value $gitignoreContent
    Write-Host ".gitignore created and updated." -ForegroundColor Green
}

Write-Host "`nDone." -ForegroundColor Green

exit 0  # Success
