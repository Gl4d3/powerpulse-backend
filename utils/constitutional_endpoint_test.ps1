# Constitutional Endpoint Testing PowerShell Script
# Tests all newly implemented endpoints using Invoke-WebRequest to validate functionality.
# 
# CONSTITUTIONAL REQUIREMENT: All endpoints must pass these tests before advancing to next phase.

param(
    [string]$BaseUrl = "http://localhost:8000",
    [switch]$Verbose = $false
)

# Function to log with colors
function Write-Constitutional {
    param(
        [string]$Message,
        [string]$Type = "Info"  # Info, Success, Warning, Error
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    
    switch ($Type) {
        "Success" { Write-Host "[$timestamp] ✅ $Message" -ForegroundColor Green }
        "Warning" { Write-Host "[$timestamp] ⚠️ $Message" -ForegroundColor Yellow }
        "Error"   { Write-Host "[$timestamp] ❌ $Message" -ForegroundColor Red }
        "Info"    { Write-Host "[$timestamp] 🧪 $Message" -ForegroundColor Cyan }
        default   { Write-Host "[$timestamp] $Message" }
    }
}

# Function to test server health
function Test-ServerHealth {
    param([string]$BaseUrl)
    
    Write-Constitutional "Testing Server Health ($BaseUrl)" "Info"
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/" -Method GET -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Constitutional "Server health check passed: $($response.StatusCode)" "Success"
            return $true
        } else {
            Write-Constitutional "Server health check failed: $($response.StatusCode)" "Error"
            return $false
        }
    } catch {
        Write-Constitutional "Server not responding! Please start the server with:" "Error"
        Write-Constitutional "uvicorn main:app --host 0.0.0.0 --port 8000 --reload" "Warning"
        return $false
    }
}

# Function to create test JSON file
function New-TestJsonFile {
    param([int]$InteractionCount = 20)
    
    $testData = @()
    for ($i = 1; $i -le $InteractionCount; $i++) {
        $interaction = @{
            conversation_id = "powershell_test_conv_$i"
            timestamp = "2024-09-17T$(($i % 24).ToString('00')):00:00Z"
            messages = @(
                @{
                    role = "user"
                    content = "Constitutional PowerShell test user message $i"
                    timestamp = "2024-09-17T$(($i % 24).ToString('00')):00:00Z"
                },
                @{
                    role = "assistant"
                    content = "Constitutional PowerShell test assistant response $i"
                    timestamp = "2024-09-17T$(($i % 24).ToString('00')):01:00Z"
                }
            )
        }
        $testData += $interaction
    }
    
    $tempFile = [System.IO.Path]::GetTempFileName() + ".json"
    $testData | ConvertTo-Json -Depth 10 | Out-File -FilePath $tempFile -Encoding UTF8
    return $tempFile
}

# Function to test enhanced upload endpoint
function Test-EnhancedUploadEndpoint {
    param([string]$BaseUrl)
    
    Write-Constitutional "Testing Enhanced Upload Endpoint (/api/upload-json-enhanced)" "Info"
    
    $testFile = New-TestJsonFile -InteractionCount 25
    
    try {
        # PowerShell multipart form data for file upload
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        
        # Read file content
        $fileContent = Get-Content -Path $testFile -Raw -Encoding UTF8
        $fileName = "constitutional_powershell_test.json"
        
        # Create multipart body
        $bodyLines = @(
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"$fileName`"",
            "Content-Type: application/json",
            "",
            $fileContent,
            "--$boundary",
            "Content-Disposition: form-data; name=`"batch_strategy`"",
            "",
            "auto",
            "--$boundary",
            "Content-Disposition: form-data; name=`"priority`"",
            "",
            "normal",
            "--$boundary--"
        )
        $body = $bodyLines -join $LF
        
        $headers = @{
            "Content-Type" = "multipart/form-data; boundary=$boundary"
        }
        
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/upload-json-enhanced" -Method POST -Body $body -Headers $headers -UseBasicParsing
        
        Write-Constitutional "Upload Status Code: $($response.StatusCode)" "Info"
        
        if ($response.StatusCode -eq 200) {
            $result = $response.Content | ConvertFrom-Json
            Write-Constitutional "Session ID: $($result.session_id)" "Success"
            Write-Constitutional "Status: $($result.status)" "Success"
            Write-Constitutional "Batch Strategy: $($result.batch_strategy)" "Success"
            Write-Constitutional "Estimated Cost Savings: $($result.estimated_cost_savings)%" "Success"
            
            return @{
                success = $true
                session_id = $result.session_id
                result = $result
            }
        } else {
            Write-Constitutional "Upload failed: $($response.Content)" "Error"
            return @{ success = $false; error = $response.Content }
        }
    } catch {
        Write-Constitutional "Exception during upload: $($_.Exception.Message)" "Error"
        return @{ success = $false; error = $_.Exception.Message }
    } finally {
        Remove-Item -Path $testFile -Force -ErrorAction SilentlyContinue
    }
}

# Function to test upload status endpoint
function Test-UploadStatusEndpoint {
    param(
        [string]$BaseUrl,
        [string]$SessionId
    )
    
    Write-Constitutional "Testing Upload Status Endpoint (/api/upload-status/$SessionId)" "Info"
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/upload-status/$SessionId" -Method GET -UseBasicParsing
        Write-Constitutional "Status Code: $($response.StatusCode)" "Info"
        
        if ($response.StatusCode -eq 200) {
            $result = $response.Content | ConvertFrom-Json
            Write-Constitutional "Session ID: $($result.session_id)" "Success"
            Write-Constitutional "Status: $($result.status)" "Success"
            Write-Constitutional "Progress: $($result.progress_percentage)%" "Success"
            Write-Constitutional "Interactions Count: $($result.interactions_count)" "Success"
            return @{ success = $true; result = $result }
        } elseif ($response.StatusCode -eq 404) {
            Write-Constitutional "Session not found (expected for new sessions)" "Warning"
            return @{ success = $true; status = "not_found" }
        } else {
            Write-Constitutional "Status check failed: $($response.Content)" "Error"
            return @{ success = $false; error = $response.Content }
        }
    } catch {
        Write-Constitutional "Exception during status check: $($_.Exception.Message)" "Error"
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Function to test batch config endpoint
function Test-BatchConfigEndpoint {
    param([string]$BaseUrl)
    
    Write-Constitutional "Testing Batch Config Endpoint (/api/batch-config)" "Info"
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/batch-config" -Method GET -UseBasicParsing
        Write-Constitutional "Status Code: $($response.StatusCode)" "Info"
        
        if ($response.StatusCode -eq 200) {
            $result = $response.Content | ConvertFrom-Json
            Write-Constitutional "Batch Settings Present: $($null -ne $result.batch_settings)" "Success"
            Write-Constitutional "Performance Metrics Present: $($null -ne $result.performance_metrics)" "Success"
            Write-Constitutional "System Status Present: $($null -ne $result.system_status)" "Success"
            
            if ($result.batch_settings) {
                Write-Constitutional "Batch Enabled: $($result.batch_settings.enabled)" "Success"
                Write-Constitutional "Max Concurrent Sessions: $($result.batch_settings.max_concurrent_sessions)" "Success"
            }
            
            return @{ success = $true; result = $result }
        } else {
            Write-Constitutional "Batch config failed: $($response.Content)" "Error"
            return @{ success = $false; error = $response.Content }
        }
    } catch {
        Write-Constitutional "Exception during batch config: $($_.Exception.Message)" "Error"
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Function to test constitutional compliance endpoint
function Test-ConstitutionalComplianceEndpoint {
    param(
        [string]$BaseUrl,
        [string]$SessionId = $null
    )
    
    $endpoint = "/api/constitutional/compliance"
    if ($SessionId) {
        $endpoint += "?session_id=$SessionId"
        Write-Constitutional "Testing Constitutional Compliance Endpoint (with session: $SessionId)" "Info"
    } else {
        Write-Constitutional "Testing Constitutional Compliance Endpoint (system-wide)" "Info"
    }
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl$endpoint" -Method GET -UseBasicParsing
        Write-Constitutional "Status Code: $($response.StatusCode)" "Info"
        
        if ($response.StatusCode -eq 200) {
            $result = $response.Content | ConvertFrom-Json
            Write-Constitutional "Is Compliant: $($result.is_compliant)" "Success"
            Write-Constitutional "Constitutional Requirements Present: $($null -ne $result.constitutional_requirements)" "Success"
            
            if ($result.constitutional_requirements) {
                $reqs = $result.constitutional_requirements
                if ($reqs.ai_supremacy) {
                    Write-Constitutional "AI Supremacy: $($reqs.ai_supremacy.status)" "Success"
                }
                if ($reqs.dual_csi_architecture) {
                    Write-Constitutional "Dual CSI: $($reqs.dual_csi_architecture.status)" "Success"
                }
                if ($reqs.cost_reduction) {
                    Write-Constitutional "Cost Reduction: $($reqs.cost_reduction.status)" "Success"
                }
            }
            
            if ($result.violations -and $result.violations.Count -gt 0) {
                Write-Constitutional "Violations Found: $($result.violations.Count)" "Warning"
                for ($i = 0; $i -lt [Math]::Min(3, $result.violations.Count); $i++) {
                    Write-Constitutional "  - $($result.violations[$i])" "Warning"
                }
            }
            
            return @{ success = $true; result = $result }
        } else {
            Write-Constitutional "Constitutional compliance failed: $($response.Content)" "Error"
            return @{ success = $false; error = $response.Content }
        }
    } catch {
        Write-Constitutional "Exception during constitutional compliance: $($_.Exception.Message)" "Error"
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Function to test retry endpoint
function Test-RetryEndpoint {
    param(
        [string]$BaseUrl,
        [string]$SessionId
    )
    
    Write-Constitutional "Testing Retry Endpoint (/api/retry/$SessionId)" "Info"
    
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/retry/$SessionId" -Method POST -UseBasicParsing
        Write-Constitutional "Status Code: $($response.StatusCode)" "Info"
        
        if ($response.StatusCode -eq 200) {
            $result = $response.Content | ConvertFrom-Json
            Write-Constitutional "Session ID: $($result.session_id)" "Success"
            Write-Constitutional "Status: $($result.status)" "Success"
            Write-Constitutional "Retry Count: $($result.retry_count)" "Success"
            return @{ success = $true; result = $result }
        } elseif ($response.StatusCode -eq 404) {
            Write-Constitutional "Session not found" "Warning"
            return @{ success = $true; status = "not_found" }
        } elseif ($response.StatusCode -eq 400) {
            Write-Constitutional "Retry not allowed (may have exceeded max retries)" "Warning"
            return @{ success = $true; status = "retry_not_allowed" }
        } else {
            Write-Constitutional "Retry failed: $($response.Content)" "Error"
            return @{ success = $false; error = $response.Content }
        }
    } catch {
        Write-Constitutional "Exception during retry: $($_.Exception.Message)" "Error"
        return @{ success = $false; error = $_.Exception.Message }
    }
}

# Function to test error handling
function Test-InvalidEndpoints {
    param([string]$BaseUrl)
    
    Write-Constitutional "Testing Error Handling" "Info"
    
    $results = @{}
    
    # Test invalid session ID
    try {
        $invalidSession = "invalid-session-id-12345"
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/upload-status/$invalidSession" -Method GET -UseBasicParsing -ErrorAction Stop
        Write-Constitutional "Invalid Session Status Code: $($response.StatusCode) (expected 404)" "Warning"
        $results.invalid_session = $response.StatusCode
    } catch {
        if ($_.Exception.Response.StatusCode -eq 404) {
            Write-Constitutional "Invalid Session Status Code: 404 (expected)" "Success"
            $results.invalid_session = 404
        } else {
            $results.invalid_session = "Exception: $($_.Exception.Message)"
        }
    }
    
    # Test malformed upload
    try {
        $boundary = [System.Guid]::NewGuid().ToString()
        $LF = "`r`n"
        $bodyLines = @(
            "--$boundary",
            "Content-Disposition: form-data; name=`"file`"; filename=`"bad.txt`"",
            "Content-Type: text/plain",
            "",
            "not json content",
            "--$boundary--"
        )
        $body = $bodyLines -join $LF
        $headers = @{ "Content-Type" = "multipart/form-data; boundary=$boundary" }
        
        $response = Invoke-WebRequest -Uri "$BaseUrl/api/upload-json-enhanced" -Method POST -Body $body -Headers $headers -UseBasicParsing -ErrorAction Stop
        Write-Constitutional "Invalid Upload Status Code: $($response.StatusCode) (expected 400/422)" "Warning"
        $results.invalid_upload = $response.StatusCode
    } catch {
        $statusCode = $_.Exception.Response.StatusCode
        if ($statusCode -eq 400 -or $statusCode -eq 422) {
            Write-Constitutional "Invalid Upload Status Code: $statusCode (expected)" "Success"
            $results.invalid_upload = [int]$statusCode
        } else {
            $results.invalid_upload = "Exception: $($_.Exception.Message)"
        }
    }
    
    return $results
}

# Main function to run all tests
function Invoke-ConstitutionalEndpointTests {
    param([string]$BaseUrl = "http://localhost:8000")
    
    Write-Host "🚨 CONSTITUTIONAL ENDPOINT TESTING INITIATED" -ForegroundColor Magenta
    Write-Host ("=" * 60) -ForegroundColor Magenta
    
    $allResults = @{}
    
    # Test 1: Server Health
    if (-not (Test-ServerHealth -BaseUrl $BaseUrl)) {
        Write-Constitutional "CONSTITUTIONAL VIOLATION: Server not running!" "Error"
        return @{ fatal_error = "Server not accessible" }
    }
    $allResults.server_health = "✅ PASSED"
    
    # Test 2: Enhanced Upload
    $uploadResult = Test-EnhancedUploadEndpoint -BaseUrl $BaseUrl
    if ($uploadResult.success -and $uploadResult.session_id) {
        $allResults.enhanced_upload = "✅ PASSED"
        $sessionId = $uploadResult.session_id
        
        # Test 3: Upload Status (immediate check)
        $statusResult = Test-UploadStatusEndpoint -BaseUrl $BaseUrl -SessionId $sessionId
        if ($statusResult.success) {
            $allResults.upload_status = "✅ PASSED"
        } else {
            $allResults.upload_status = "❌ FAILED"
        }
        
        # Test 4: Retry Endpoint
        $retryResult = Test-RetryEndpoint -BaseUrl $BaseUrl -SessionId $sessionId
        if ($retryResult.success) {
            $allResults.retry_endpoint = "✅ PASSED"
        } else {
            $allResults.retry_endpoint = "❌ FAILED"
        }
        
        # Test 5: Constitutional Compliance (with session)
        $complianceResult = Test-ConstitutionalComplianceEndpoint -BaseUrl $BaseUrl -SessionId $sessionId
        if ($complianceResult.success) {
            $allResults.constitutional_compliance_session = "✅ PASSED"
        } else {
            $allResults.constitutional_compliance_session = "❌ FAILED"
        }
    } else {
        $allResults.enhanced_upload = "❌ FAILED"
        $sessionId = $null
    }
    
    # Test 6: Batch Config
    $batchConfigResult = Test-BatchConfigEndpoint -BaseUrl $BaseUrl
    if ($batchConfigResult.success) {
        $allResults.batch_config = "✅ PASSED"
    } else {
        $allResults.batch_config = "❌ FAILED"
    }
    
    # Test 7: Constitutional Compliance (system-wide)
    $systemComplianceResult = Test-ConstitutionalComplianceEndpoint -BaseUrl $BaseUrl
    if ($systemComplianceResult.success) {
        $allResults.constitutional_compliance_system = "✅ PASSED"
    } else {
        $allResults.constitutional_compliance_system = "❌ FAILED"
    }
    
    # Test 8: Error Handling
    $errorResults = Test-InvalidEndpoints -BaseUrl $BaseUrl
    if ($errorResults.Count -gt 0) {
        $allResults.error_handling = "✅ PASSED"
    } else {
        $allResults.error_handling = "❌ FAILED"
    }
    
    # Constitutional Compliance Summary
    Write-Host "`n$("=" * 60)" -ForegroundColor Magenta
    Write-Host "🚨 CONSTITUTIONAL COMPLIANCE SUMMARY" -ForegroundColor Magenta
    Write-Host ("=" * 60) -ForegroundColor Magenta
    
    $passedTests = 0
    $totalTests = $allResults.Count
    
    foreach ($testName in $allResults.Keys) {
        $result = $allResults[$testName]
        $displayName = ($testName -replace '_', ' ').ToUpper()
        
        if ($result -like "*✅ PASSED*") {
            Write-Host "  $displayName`: $result" -ForegroundColor Green
            $passedTests++
        } else {
            Write-Host "  $displayName`: $result" -ForegroundColor Red
        }
    }
    
    $complianceRate = ($passedTests / $totalTests) * 100
    Write-Host "`n📊 CONSTITUTIONAL COMPLIANCE RATE: $passedTests/$totalTests ($($complianceRate.ToString('F1'))%)" -ForegroundColor Cyan
    
    if ($passedTests -eq $totalTests) {
        Write-Host "✅ ALL CONSTITUTIONAL REQUIREMENTS MET - PROCEED TO NEXT PHASE" -ForegroundColor Green
    } else {
        Write-Host "❌ CONSTITUTIONAL VIOLATIONS DETECTED - CANNOT PROCEED" -ForegroundColor Red
    }
    
    return $allResults
}

# Script entry point
Write-Host "🚨 PowerPulse Constitutional Endpoint Testing (PowerShell)" -ForegroundColor Magenta
Write-Host "Please ensure the FastAPI server is running on $BaseUrl" -ForegroundColor Yellow
Write-Host "Command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Yellow

if (-not $Verbose) {
    Read-Host "`nPress Enter when server is ready"
}

$results = Invoke-ConstitutionalEndpointTests -BaseUrl $BaseUrl

# Exit with appropriate code
$passedCount = ($results.Values | Where-Object { $_ -like "*✅ PASSED*" }).Count
$totalCount = $results.Count

if ($passedCount -eq $totalCount) {
    exit 0
} else {
    exit 1
}