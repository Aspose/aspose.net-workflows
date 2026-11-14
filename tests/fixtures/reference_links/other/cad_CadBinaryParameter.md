---
linkTitle: "Class CadBinaryParameter"
title: "Class CadBinaryParameter"
description: "The Cad binary parameter."
summary: "The Cad binary parameter."
categories:
  - Class
layout: "reference-single"
---

Namespace: [Aspose.CAD.FileFormats.Cad.CadParameters](/cad/aspose.cad.fileformats.cad.cadparameters)  
Assembly: Aspose.CAD.dll (26.9.0)  

The Cad binary parameter.

```csharp
[ComVisible(false)]
public class CadBinaryParameter : CadParameter<byte[]>
```

#### Inheritance

[object](https://learn.microsoft.com/dotnet/api/system.object) ← 
[CadParameter](/cad/aspose.cad.fileformats.cad.cadparameters.cadparameter) ← 
[CadParameter<byte\[\]\>](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter\-1.md) ← 
[CadBinaryParameter](/cad/aspose.cad.fileformats.cad.cadparameters.cadbinaryparameter)

#### Inherited Members

[CadParameter<byte\[\]\>.Init\(object\)](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter\-1.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_1\_Init\_System\_Object\_), 
[CadParameter<byte\[\]\>.Value](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter\-1.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_1\_Value), 
[CadParameter.Init\(CadEntityAttribute, CadCodeValue\)](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_Init\_Aspose\_CAD\_FileFormats\_Cad\_CadEntityAttribute\_Aspose\_CAD\_FileFormats\_Cad\_CadCodeValue\_), 
[CadParameter.Init\(CadEntityAttribute, object\)](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_Init\_Aspose\_CAD\_FileFormats\_Cad\_CadEntityAttribute\_System\_Object\_), 
[CadParameter.Init\(CadCodeValue\)](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_Init\_Aspose\_CAD\_FileFormats\_Cad\_CadCodeValue\_), 
[CadParameter.Init\(object\)](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_Init\_System\_Object\_), 
[CadParameter.Type](Aspose.CAD.FileFormats.Cad.CadParameters.CadParameter.md\#Aspose\_CAD\_FileFormats\_Cad\_CadParameters\_CadParameter\_Type), 
[object.GetType\(\)](https://learn.microsoft.com/dotnet/api/system.object.gettype), 
[object.MemberwiseClone\(\)](https://learn.microsoft.com/dotnet/api/system.object.memberwiseclone), 
[object.ToString\(\)](https://learn.microsoft.com/dotnet/api/system.object.tostring), 
[object.Equals\(object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\)), 
[object.Equals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.equals\#system\-object\-equals\(system\-object\-system\-object\)), 
[object.ReferenceEquals\(object?, object?\)](https://learn.microsoft.com/dotnet/api/system.object.referenceequals), 
[object.GetHashCode\(\)](https://learn.microsoft.com/dotnet/api/system.object.gethashcode)

## Constructors

### <a id="Aspose_CAD_FileFormats_Cad_CadParameters_CadBinaryParameter__ctor_Aspose_CAD_FileFormats_Cad_CadEntityAttribute_"></a> CadBinaryParameter\(CadEntityAttribute\)

Initializes a new instance of the Aspose.CAD.FileFormats.Cad.CadParameters.CadBinaryParameter class.

```csharp
public CadBinaryParameter(CadEntityAttribute type)
```

#### Parameters

`type` [CadEntityAttribute](/cad/aspose.cad.fileformats.cad.cadentityattribute)

The type of the parameter.

## Properties

### <a id="Aspose_CAD_FileFormats_Cad_CadParameters_CadBinaryParameter_Data"></a> Data

Gets or sets the value.

```csharp
public byte[] Data { get; set; }
```

#### Property Value

 [byte](https://learn.microsoft.com/dotnet/api/system.byte)\[\]

## Methods

### <a id="Aspose_CAD_FileFormats_Cad_CadParameters_CadBinaryParameter_Init_Aspose_CAD_FileFormats_Cad_CadCodeValue_"></a> Init\(CadCodeValue\)

Initialize the specified value.

```csharp
public override void Init(CadCodeValue value)
```

#### Parameters

`value` [CadCodeValue](/cad/aspose.cad.fileformats.cad.cadcodevalue)

The value to assign.
