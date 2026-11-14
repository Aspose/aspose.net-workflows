---
linkTitle: "Class OrganizerBaseOptions"
title: "Class OrganizerBaseOptions"
description: "Represents base options for plugins."
summary: "Represents base options for plugins."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.Pdf.LowCode](/pdf/aspose.pdf.lowcode)  
Assembly: Aspose.PDF.dll (26.10.0)  

Represents base options for plugins.

```csharp
public class OrganizerBaseOptions : IPluginOptions
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[OrganizerBaseOptions](/pdf/aspose.pdf.lowcode.organizerbaseoptions)

#### Derived

[CompressOptions](/pdf/aspose.pdf.lowcode.compressoptions), 
[DecryptionOptions](/pdf/aspose.pdf.lowcode.decryptionoptions), 
[EncryptionOptions](/pdf/aspose.pdf.lowcode.encryptionoptions), 
[MergeOptions](/pdf/aspose.pdf.lowcode.mergeoptions), 
[OptimizeOptions](/pdf/aspose.pdf.lowcode.optimizeoptions), 
[ResizeOptions](/pdf/aspose.pdf.lowcode.resizeoptions), 
[RotateOptions](/pdf/aspose.pdf.lowcode.rotateoptions), 
[SignOptions](/pdf/aspose.pdf.lowcode.signoptions), 
[SplitOptions](/pdf/aspose.pdf.lowcode.splitoptions)

#### Implements

[IPluginOptions](/pdf/aspose.pdf.lowcode.ipluginoptions)

## Properties

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_CloseInputStreams"></a> CloseInputStreams

Close input streams after operation completed.

```csharp
public bool CloseInputStreams { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_CloseOutputStreams"></a> CloseOutputStreams

Close output streams after operation completed.

```csharp
public bool CloseOutputStreams { get; set; }
```

#### Property Value

 [bool](https://learn.microsoft.com/dotnet/api/system.boolean)

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_Inputs"></a> Inputs

Returns OrganizerOptions plugin data collection.

```csharp
public List<IDataSource> Inputs { get; }
```

#### Property Value

 [List](https://learn.microsoft.com/dotnet/api/system.collections.generic.list\-1)<[IDataSource](/pdf/aspose.pdf.lowcode.idatasource)\>

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_Outputs"></a> Outputs

Gets collection of added targets for saving operation results.

```csharp
public List<IDataSource> Outputs { get; }
```

#### Property Value

 [List](https://learn.microsoft.com/dotnet/api/system.collections.generic.list\-1)<[IDataSource](/pdf/aspose.pdf.lowcode.idatasource)\>

## Methods

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_AddInput_Aspose_Pdf_LowCode_IDataSource_"></a> AddInput\(IDataSource\)

Adds new data source to the PdfOrganizer plugin data collection.

```csharp
public void AddInput(IDataSource dataSource)
```

#### Parameters

`dataSource` [IDataSource](/pdf/aspose.pdf.lowcode.idatasource)

Data source to add.

### <a id="Aspose_Pdf_LowCode_OrganizerBaseOptions_AddOutput_Aspose_Pdf_LowCode_IDataSource_"></a> AddOutput\(IDataSource\)

Adds new data source to the PdfOrganizer plugin data collection.

```csharp
public void AddOutput(IDataSource saveDataSource)
```

#### Parameters

`saveDataSource` [IDataSource](/pdf/aspose.pdf.lowcode.idatasource)

Data source (file or stream) for saving operation results.

#### Exceptions

 [NotImplementedException](https://learn.microsoft.com/dotnet/api/system.notimplementedexception)
