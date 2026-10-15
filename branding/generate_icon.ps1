$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
if (-not ('BayaIcon' -as [type])) {
Add-Type -ReferencedAssemblies System.Drawing -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;

public static class BayaIcon
{
    private static PointF[] Points(params float[] values)
    {
        PointF[] result = new PointF[values.Length / 2];
        for (int i = 0; i < result.Length; ++i) result[i] = new PointF(values[i * 2], values[i * 2 + 1]);
        return result;
    }
    private static byte[] Render(int size)
    {
        const int antialias = 4;
        using (Bitmap large = new Bitmap(size * antialias, size * antialias, PixelFormat.Format32bppArgb))
        using (Graphics graphics = Graphics.FromImage(large))
        {
            graphics.SmoothingMode = SmoothingMode.AntiAlias;
            graphics.PixelOffsetMode = PixelOffsetMode.HighQuality;
            graphics.ScaleTransform(size * antialias / 256f, size * antialias / 256f);
            using (GraphicsPath tile = new GraphicsPath())
            {
                tile.AddArc(8, 8, 100, 100, 180, 90);
                tile.AddArc(148, 8, 100, 100, 270, 90);
                tile.AddArc(148, 148, 100, 100, 0, 90);
                tile.AddArc(8, 148, 100, 100, 90, 90);
                tile.CloseFigure();
                using (LinearGradientBrush brush = new LinearGradientBrush(new PointF(8, 8), new PointF(248, 248), Color.FromArgb(41, 52, 59), Color.FromArgb(18, 26, 32)))
                    graphics.FillPath(brush, tile);
                using (Pen stroke = new Pen(Color.FromArgb(67, 84, 91), 2f)) graphics.DrawPath(stroke, tile);
            }
            using (SolidBrush shadow = new SolidBrush(Color.FromArgb(23, 111, 112)))
                graphics.FillPolygon(shadow, Points(76,54,155,54,191,86,191,123,174,140,196,161,196,199,161,228,76,228));
            using (GraphicsPath face = new GraphicsPath(FillMode.Alternate))
            {
                face.AddPolygon(Points(62,40,141,40,177,72,177,109,160,126,182,147,182,185,147,214,62,214));
                face.AddPolygon(Points(95,72,95,111,133,111,145,99,145,84,131,72));
                face.AddPolygon(Points(95,143,95,182,137,182,149,171,149,156,135,143));
                using (LinearGradientBrush brush = new LinearGradientBrush(new PointF(62,40),new PointF(158,214),Color.FromArgb(165,255,226),Color.FromArgb(67,195,172)))
                    graphics.FillPath(brush, face);
            }
            using (SolidBrush highlight = new SolidBrush(Color.FromArgb(89,209,255,241)))
                graphics.FillPolygon(highlight,Points(62,40,141,40,177,72,163,83,132,56,76,56,76,200,62,214));
            using (SolidBrush lower = new SolidBrush(Color.FromArgb(48,149,140)))
                graphics.FillPolygon(lower,Points(147,214,182,185,196,199,161,228,76,228,62,214));
            using (Bitmap output = new Bitmap(size, size, PixelFormat.Format32bppArgb))
            using (Graphics downsample = Graphics.FromImage(output))
            using (MemoryStream stream = new MemoryStream())
            {
                downsample.InterpolationMode = InterpolationMode.HighQualityBicubic;
                downsample.CompositingQuality = CompositingQuality.HighQuality;
                downsample.DrawImage(large, new Rectangle(0,0,size,size));
                output.Save(stream, ImageFormat.Png);
                return stream.ToArray();
            }
        }
    }
    public static void Write(string directory)
    {
        int[] sizes = {16,24,32,48,64,128,256};
        List<byte[]> images = new List<byte[]>();
        foreach (int size in sizes) images.Add(Render(size));
        using (BinaryWriter writer = new BinaryWriter(File.Create(Path.Combine(directory,"Baya3D.ico"))))
        {
            writer.Write((ushort)0); writer.Write((ushort)1); writer.Write((ushort)sizes.Length);
            int offset = 6 + 16 * sizes.Length;
            for (int i = 0; i < sizes.Length; ++i)
            {
                writer.Write((byte)(sizes[i] == 256 ? 0 : sizes[i]));
                writer.Write((byte)(sizes[i] == 256 ? 0 : sizes[i]));
                writer.Write((byte)0); writer.Write((byte)0);
                writer.Write((ushort)1); writer.Write((ushort)32);
                writer.Write(images[i].Length); writer.Write(offset);
                offset += images[i].Length;
            }
            foreach (byte[] png in images) writer.Write(png);
        }
        File.WriteAllBytes(Path.Combine(directory,"Baya3D.png"),Render(512));
    }
}
'@
}
[BayaIcon]::Write($PSScriptRoot)
