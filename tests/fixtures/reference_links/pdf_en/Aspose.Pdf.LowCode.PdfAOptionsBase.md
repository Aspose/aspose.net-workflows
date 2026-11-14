---
linkTitle: "Class PdfAOptionsBase"
title: "Class PdfAOptionsBase"
description: "Represents the base class for the  plugin options. This class provides properties and methods for configuring the PDF/A conversion and validation process."
summary: "Represents the base class for the  plugin options. This class provides properties and methods for configuring the PDF/A conversion and validation process."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Pdf.LowCode](/pdf/aspose.pdf.lowcode)  
Assembly: Aspose.PDF.dll (26.10.0)  

Represents the base class for the Aspose.Pdf.LowCode.PdfAConverter plugin options.
This class provides properties and methods for configuring the PDF/A conversion and validation process.

```csharp
public abstract class PdfAOptionsBase : IPluginOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[PdfAOptionsBase](/pdf/aspose.pdf.lowcode.pdfaoptionsbase)

#### Derived

[PdfAConvertOptions](/pdf/aspose.pdf.lowcode.pdfaconvertoptions), 
[PdfAValidateOptions](/pdf/aspose.pdf.lowcode.pdfavalidateoptions)

#### Implements

[IPluginOptions](/pdf/aspose.pdf.lowcode.ipluginoptions)

## Constructors

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase__ctor"></a> PdfAOptionsBase\(\)

```csharp
protected PdfAOptionsBase()
```

## Properties

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_AlignText"></a> AlignText

Gets or sets a value indicating whether additional means are necessary to preserve text alignment
during the PDF/A conversion process.

```csharp
public bool AlignText { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

When set to <a href="https://learn.microsoft.com/dotnet/csharp/language-reference/builtin-types/bool">true</a>, the conversion process will attempt to restore the original text segment bounds. 
For the most of the documents there is no need to change this property from the default <a href="https://learn.microsoft.com/dotnet/csharp/language-reference/builtin-types/bool">false</a> value,
as the text alignment doesn't change during the default conversion process.

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_ErrorAction"></a> ErrorAction

Gets or sets the action to be taken for objects that cannot be converted.

```csharp
public ConvertErrorAction ErrorAction { get; set; }
```

#### Property Value

 [ConvertErrorAction](/pdf/aspose.pdf.converterroraction)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_ExcludeFontsStrategy"></a> ExcludeFontsStrategy

Gets or sets the strategy for removing fonts to minimize the output file size during the PDF/A conversion process.

```csharp
public PdfFormatConversionOptions.RemoveFontsStrategy ExcludeFontsStrategy { get; set; }
```

#### Property Value

 [PdfFormatConversionOptions](/pdf/aspose.pdf.pdfformatconversionoptions).[RemoveFontsStrategy](/pdf/aspose.pdf.pdfformatconversionoptions.removefontsstrategy)

#### Remarks

This property allows you to control how fonts are handled during the conversion process. 
You can choose to remove duplicated fonts, remove similar fonts with different widths, or subset fonts.

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_FontEmbeddingOptions"></a> FontEmbeddingOptions

Gets the options to process fonts that cannot be embedded into the document.

```csharp
public FontEmbeddingOptions FontEmbeddingOptions { get; }
```

#### Property Value

 [FontEmbeddingOptions](/pdf/aspose.pdf.fontembeddingoptions)

#### Remarks

The PDF/A standard requires that all fonts must be embedded into the document. 
This property provides options for handling cases when it's not possible to embed some fonts because they are absent on the destination PC.

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_IccProfileFileName"></a> IccProfileFileName

Gets or sets the filename of the ICC (International Color Consortium) profile to be used for the PDF/A conversion in place of
the default one.

```csharp
public string IccProfileFileName { get; set; }
```

#### Property Value

 [string](https://learn.microsoft.com/dotnet/api/system.string)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_Inputs"></a> Inputs

Gets collection of data sources

```csharp
public List<IDataSource> Inputs { get; }
```

#### Property Value

 [List](https://learn.microsoft.com/dotnet/api/system.collections.generic.list\-1)<[IDataSource](/pdf/aspose.pdf.lowcode.idatasource)\>

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_IsLowMemoryMode"></a> IsLowMemoryMode

Gets or sets a value indicating whether the low memory mode is enabled during the PDF/A conversion process.

```csharp
public bool IsLowMemoryMode { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_LogOutputSource"></a> LogOutputSource

Gets or sets the data source for the log output.

```csharp
public IDataSource LogOutputSource { get; set; }
```

#### Property Value

 [IDataSource](/pdf/aspose.pdf.lowcode.idatasource)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_NonSpecificationFlags"></a> NonSpecificationFlags

Gets the flags that control the PDF/A conversion for cases when the source PDF document doesn't 
correspond to the PDF specification.

```csharp
public PdfANonSpecificationFlags NonSpecificationFlags { get; }
```

#### Property Value

 [PdfANonSpecificationFlags](/pdf/aspose.pdf.pdfanonspecificationflags)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_OptimizeFileSize"></a> OptimizeFileSize

Gets or sets a value indicating whether to try to reduce the file size during the PDF/A conversion process.

```csharp
public bool OptimizeFileSize { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

#### Remarks

When set to <a href="https://learn.microsoft.com/dotnet/csharp/language-reference/builtin-types/bool">true</a>, the conversion process will attempt to minimize the resulting file size. 
This might affect the conversion process performance.

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_PdfAVersion"></a> PdfAVersion

Gets or sets the version of the PDF/A standard to be used for validation or conversion.

```csharp
public PdfAStandardVersion PdfAVersion { get; set; }
```

#### Property Value

 [PdfAStandardVersion](/pdf/aspose.pdf.lowcode.pdfastandardversion)

#### Remarks

The PDF/A standard version is used to determine the compliance level for PDF/A validation and conversion. 
If the version is set to Aspose.Pdf.LowCode.PdfAStandardVersion.Auto, the system will automatically determine
the appropriate PDF/A standard version for validation based on the document metadata.
For the PDF/A conversion process the Aspose.Pdf.LowCode.PdfAStandardVersion.Auto defaults to the PDF/A-1b standard version.

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_PuaSymbolsProcessingStrategy"></a> PuaSymbolsProcessingStrategy

Gets or sets the strategy for processing Private Use Area (PUA) symbols in the PDF document.

```csharp
public PdfFormatConversionOptions.PuaProcessingStrategy PuaSymbolsProcessingStrategy { get; set; }
```

#### Property Value

 [PdfFormatConversionOptions](/pdf/aspose.pdf.pdfformatconversionoptions).[PuaProcessingStrategy](/pdf/aspose.pdf.pdfformatconversionoptions.puaprocessingstrategy)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_SoftMaskAction"></a> SoftMaskAction

Gets or sets the action to be taken during the conversion of images with soft masks.

```csharp
public ConvertSoftMaskAction SoftMaskAction { get; set; }
```

#### Property Value

 [ConvertSoftMaskAction](/pdf/aspose.pdf.convertsoftmaskaction)

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_SymbolicFontEncodingStrategy"></a> SymbolicFontEncodingStrategy

Gets or sets the strategy for encoding symbolic fonts when converting to PDF/A format.

```csharp
public PdfASymbolicFontEncodingStrategy SymbolicFontEncodingStrategy { get; set; }
```

#### Property Value

 [PdfASymbolicFontEncodingStrategy](/pdf/aspose.pdf.pdfasymbolicfontencodingstrategy)

#### Remarks

This property allows you to control what CMap subtable would be copied into the result document in cases when the original
TrueType symbolic font in the source document contains multiple CMap subtables.

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_UnicodeProcessingRules"></a> UnicodeProcessingRules

Gets or sets the rules for processing ToUnicode CMap tables and not linked to Unicode symbols during the PDF/A conversion process.

```csharp
public ToUnicodeProcessingRules UnicodeProcessingRules { get; set; }
```

#### Property Value

 [ToUnicodeProcessingRules](/pdf/aspose.pdf.tounicodeprocessingrules)

## Methods

### <a id="Aspose_Pdf_LowCode_PdfAOptionsBase_AddInput_Aspose_Pdf_LowCode_IDataSource_"></a> AddInput\(IDataSource\)

Adds new data source to the collection

```csharp
public void AddInput(IDataSource dataSource)
```

#### Parameters

`dataSource` [IDataSource](/pdf/aspose.pdf.lowcode.idatasource)
