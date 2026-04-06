# Gold Price Pusher Script
param([switch]$Once, [switch]$Test)

$Config = @{
    WechatUserId = "o9cq80ydCU-hCzz00QLNmz00JMdg@im.wechat"
    ApiUrl = "https://api.jisuapi.com/gold/london?appkey=33c976a06affe275"
}

function Get-GoldPrice {
    try {
        $response = Invoke-RestMethod -Uri $Config.ApiUrl -Method Get -TimeoutSec 30
        if ($response.status -ne 0) { return $null }
        $gold = $response.result[0]
        if (-not $gold) { return $null }
        $priceUsd = [double]$gold.price
        $priceCny = [math]::Round($priceUsd / 31.1035 * 6.8859, 2)
        $changePct = $gold.changepercent -replace '%', ''
        return @{ PriceUsd=$priceUsd; PriceCny=$priceCny; ChangePercent=$changePct; Time=(Get-Date -Format "yyyy-MM-dd HH:mm:ss") }
    } catch { return $null }
}

function Send-Message($msg) {
    $output = & openclaw message send --channel openclaw-weixin --target $Config.WechatUserId --message $msg 2>&1
    Write-Host $output
}

function Invoke-Push {
    $gold = Get-GoldPrice
    if ($gold) {
        $p = $gold.PriceCny
        $c = $gold.ChangePercent
        $t = $gold.Time
        $u = $gold.PriceUsd
        $arrow = if ([double]$c -ge 0) { "UP" } else { "DOWN" }
        
        # 单行格式
        $msg = "Gold: CNY $p/g | USD: `$$u/oz | Change: $c% [$arrow] | $t"
        
        Write-Host $msg
        if (-not $Test) { Send-Message $msg }
    } else {
        Write-Host "Failed to get gold price"
    }
}

if ($Test) { Write-Host "Test Mode"; Invoke-Push; exit }
if ($Once) { Invoke-Push; exit }

Write-Host "Starting Gold Price Pusher (9-12, 14-21, every 15min)"
while ($true) {
    $h = (Get-Date).Hour
    $m = (Get-Date).Minute
    if (($h -ge 9 -and $h -lt 12) -or ($h -ge 14 -and $h -lt 21)) {
        if ($m % 15 -eq 0) { Invoke-Push; Start-Sleep 60 }
    }
    Start-Sleep 30
}
