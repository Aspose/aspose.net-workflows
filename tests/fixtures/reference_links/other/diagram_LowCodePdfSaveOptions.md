---
linkTitle: "Class LowCodePdfSaveOptions"
title: "Class LowCodePdfSaveOptions"
description: "Options for saving pdf in low code way."
summary: "Options for saving pdf in low code way."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Diagram.LowCode](/diagram/aspose.diagram.lowcode)  
Assembly: Aspose.Diagram.dll (26.10.0)  

Options for saving pdf in low code way.

```csharp
public class LowCodePdfSaveOptions : LowCodeSaveOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[LowCodeSaveOptions](/diagram/aspose.diagram.lowcode.lowcodesaveoptions) ← 
[LowCodePdfSaveOptions](/diagram/aspose.diagram.lowcode.lowcodepdfsaveoptions)

#### Inherited Members

[LowCodeSaveOptions.OutputFile](Aspose.Diagram.LowCode.LowCodeSaveOptions.md\#Aspose\_Diagram\_LowCode\_LowCodeSaveOptions\_OutputFile), 
[LowCodeSaveOptions.OutputStream](Aspose.Diagram.LowCode.LowCodeSaveOptions.md\#Aspose\_Diagram\_LowCode\_LowCodeSaveOptions\_OutputStream), 
[LowCodeSaveOptions.SaveFormat](Aspose.Diagram.LowCode.LowCodeSaveOptions.md\#Aspose\_Diagram\_LowCode\_LowCodeSaveOptions\_SaveFormat)

## Constructors

### <a id="Aspose_Diagram_LowCode_LowCodePdfSaveOptions__ctor"></a> LowCodePdfSaveOptions\(\)

```csharp
public LowCodePdfSaveOptions()
```

## Properties

### <a id="Aspose_Diagram_LowCode_LowCodePdfSaveOptions_PdfOptions"></a> PdfOptions

The options for saving Pdf file.

```csharp
public PdfSaveOptions PdfOptions { get; set; }
```

#### Property Value

 [PdfSaveOptions](/diagram/aspose.diagram.saving.pdfsaveoptions)

### <a id="Aspose_Diagram_LowCode_LowCodePdfSaveOptions_SaveFormat"></a> SaveFormat

The save format for the output.
For converting to pdf, it can only be Aspose.Diagram.SaveFileFormat.Pdf.

```csharp
public override SaveFileFormat SaveFormat { get; set; }
```

#### Property Value

 [SaveFileFormat](/diagram/aspose.diagram.savefileformat)
