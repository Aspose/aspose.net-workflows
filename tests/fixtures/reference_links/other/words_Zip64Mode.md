---
linkTitle: "Enum Zip64Mode"
title: "Enum Zip64Mode"
description: "Specifies when to use ZIP64 format extensions for OOXML files."
summary: "Specifies when to use ZIP64 format extensions for OOXML files."
categories:
  - Enum
layout: "reference-single"
---

Namespace: [Aspose.Words.Saving](/words/aspose.words.saving)  
Assembly: Aspose.Words.dll (26.9.0)  

Specifies when to use ZIP64 format extensions for OOXML files.

```csharp
public enum Zip64Mode
```

## Fields

`Always = 2` 

Always use ZIP64 format extensions.



`IfNecessary = 1` 

If necessary use ZIP64 format extensions.



`Never = 0` 

Do not use ZIP64 format extensions.



## Examples

Shows how to use ZIP64 format extensions.
```csharp
Random random = new Random();
DocumentBuilder builder = new DocumentBuilder();

for (int i = 0; i < 10000; i++)
{
    using (Bitmap bmp = new Bitmap(5, 5))
    using (Graphics g = Graphics.FromImage(bmp))
    {
        g.Clear(Color.FromArgb(random.Next(0, 254), random.Next(0, 254), random.Next(0, 254)));
        using (MemoryStream ms = new MemoryStream())
        {
            bmp.Save(ms, System.Drawing.Imaging.ImageFormat.Png);
            builder.InsertImage(ms.ToArray());
        }
    }
}
OoxmlSaveOptions saveOptions =  new OoxmlSaveOptions { Zip64Mode = Zip64Mode.Always };
builder.Document.Save(ArtifactsDir + "OoxmlSaveOptions.Zip64ModeOption.docx", saveOptions);
```

## Remarks

OOXML file is a ZIP-archive that has a 4 GB (2^32 bytes) limit on uncompressed size of a file,
compressed size of a file, and total size of the archive, as well as a limit of 65,535 (2^16-1) files in archive.
ZIP64 format extensions increase the limits to 2^64.

## See Also

[OoxmlSaveOptions](/words/aspose.words.saving.ooxmlsaveoptions).[Zip64Mode](Aspose.Words.Saving.OoxmlSaveOptions.md\#Aspose\_Words\_Saving\_OoxmlSaveOptions\_Zip64Mode)
