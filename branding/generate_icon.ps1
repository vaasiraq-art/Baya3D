$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

function ConvertTo-ResizedPngBytes {
    param(
        [System.Drawing.Bitmap]$Source,
        [int]$Size
    )
    $output = [System.Drawing.Bitmap]::new($Size, $Size, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($output)
    $stream = [System.IO.MemoryStream]::new()
    try {
        $g.Clear([System.Drawing.Color]::Transparent)
        $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
        $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
        $g.DrawImage($Source, [System.Drawing.Rectangle]::new(0, 0, $Size, $Size))
        $output.Save($stream, [System.Drawing.Imaging.ImageFormat]::Png)
        return ,$stream.ToArray()
    }
    finally {
        $stream.Dispose()
        $g.Dispose()
        $output.Dispose()
    }
}

$sourcePng = Join-Path $PSScriptRoot 'Baya3D.png'
$icoOut = Join-Path $PSScriptRoot 'Baya3D.ico'
$addonAssetOut = Join-Path (Split-Path $PSScriptRoot -Parent) 'blender_maya\assets\Baya3D.png'

$sourceBmp = [System.Drawing.Bitmap]::new($sourcePng)
try {
    $sizes = @(16, 24, 32, 48, 64, 128, 256)
    $images = @()
    foreach ($sz in $sizes) {
        $images += ,(ConvertTo-ResizedPngBytes -Source $sourceBmp -Size $sz)
    }

    $fs = [System.IO.File]::Create($icoOut)
    $writer = [System.IO.BinaryWriter]::new($fs)
    try {
        $writer.Write([uint16]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]$sizes.Count)
        $offset = 6 + 16 * $sizes.Count
        for ($i = 0; $i -lt $sizes.Count; $i++) {
            $b = if ($sizes[$i] -eq 256) { [byte]0 } else { [byte]$sizes[$i] }
            $writer.Write($b)
            $writer.Write($b)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([uint16]1)
            $writer.Write([uint16]32)
            $writer.Write([int]$images[$i].Length)
            $writer.Write([int]$offset)
            $offset += $images[$i].Length
        }
        foreach ($pngBytes in $images) {
            $writer.Write($pngBytes)
        }
    }
    finally {
        $writer.Dispose()
        $fs.Dispose()
    }

    $assetBytes = ConvertTo-ResizedPngBytes -Source $sourceBmp -Size 256
    [System.IO.File]::WriteAllBytes($addonAssetOut, $assetBytes)
}
finally {
    $sourceBmp.Dispose()
}
