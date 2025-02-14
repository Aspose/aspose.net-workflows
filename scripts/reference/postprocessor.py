#!/usr/bin/env python3

import sys
import os
import re
from bs4 import BeautifulSoup
from urllib.parse import unquote

# Check if the folder path is provided
if len(sys.argv) < 2:
    print("Usage: python process_docs.py <family_name> <version>")
    sys.exit(1)

family_name = sys.argv[1]  # Pass family name (e.g., "Aspose.Words")
version = sys.argv[2]  # Pass version number (e.g., "24.12.0")
folder_path = "workspace/docfx/api"

if not os.path.exists(folder_path):
    print("Warning: The 'workspace/docfx/api' directory is missing. Skipping post-processing.")
    sys.exit(0)

print("Processing markdown files in workspace/docfx/api...")
for filename in os.listdir(folder_path):
    if filename.endswith(".md"):
        filepath = os.path.join(folder_path, filename)
        print(f"Processing {filepath}...")

# Clean the family name
family = family_name.replace("Aspose.", "").lower()  # "Aspose.Words" → "words"

def process_internal_links(content):
    """Processes internal markdown links:
       - Fix 'Namespace: [FamilyName](FamilyName.md)' before modifying other links.
       - Convert internal links to lowercase.
       - Remove .md extension.
       - Inject the cleaned family name in the link path.
    """
    try:
        # ✅ STEP 1: Fix 'Namespace' links FIRST
        content = re.sub(
            rf'Namespace: \[{re.escape(family_name)}\]\(\s*{re.escape(family_name)}\.md\s*\)',
            f'Namespace: [{family_name}](/{family}/)',
            content
        )

        # ✅ STEP 2: Find and replace internal links (without https and ending with .md)
        content = re.sub(
            r'\[([^\]]+)\]\((?!https?://)([^)]+\.md)\)',
            lambda m: f"[{m.group(1)}](/{family}/{m.group(2).lower().replace('.md', '').lstrip('/')})"
            if not m.group(2).lower().startswith(family)  # Avoid redundant family names
            else f"[{m.group(1)}](/" + m.group(2).lower().replace('.md', '').lstrip('/') + ")",
            content
        )

    except Exception as e:
        print(f"Error processing internal links: {e}")

    return content


def extract_meta_info(file_content):
    """Extract title, description, summary, and determine the category."""
    # Extract the title
    title_match = re.search(r'^#\s+<a.*?>\s*(.+)', file_content, re.MULTILINE)
    title = re.sub(r'<.*?>', '', title_match.group(1).strip()) if title_match else ''

    # Remove all <example> tags and their content
    cleaned_content = re.sub(r'<example>.*?</example>', '', file_content, flags=re.DOTALL)

    # Extract description (first meaningful text after assembly information)
    description_match = re.search(
        r'Assembly:.*?\.dll\s*\n\n\s*(.*?)(?=\n```|\Z)', cleaned_content, re.MULTILINE | re.DOTALL
    )
    description = description_match.group(1).strip() if description_match else ''

    # Strip HTML tags from description for clean summary
    summary = BeautifulSoup(description, 'html.parser').get_text() if description else ''

    # Ensure summary and description are single lines
    description = ' '.join(description.splitlines()).strip()
    summary = ' '.join(summary.splitlines()).strip()

    # Use only the first word of the title as the category
    category = title.split()[0] if title else "other"

    return title.strip(), description.strip(), summary.strip(), category


def replace_xref_tags_in_content(content):
    """Replace <xref> tags with plain text links and decode special characters."""
    if '<' in content and '>' in content:  # Check for HTML-like content
        try:
            soup = BeautifulSoup(content, 'html.parser')
            for xref in soup.find_all('xref'):
                href_text = xref.get('href', '')
                decoded_href = unquote(href_text)  # Decode special characters
                xref.replace_with(f'{decoded_href}')
            return str(soup)
        except Exception as e:
            print(f"Error parsing content with BeautifulSoup: {e}")
    return content  # Return the original content if it's not HTML-like


def clean_yaml_field(value):
    """Clean and decode YAML fields to remove special characters."""
    if not value:
        return ""

    # Decode special characters if present
    value = unquote(value)

    # Remove HTML tags if any
    if "<" in value and ">" in value:
        try:
            value = BeautifulSoup(value, 'html.parser').get_text()
        except Exception as e:
            print(f"Warning: Failed to parse HTML content: {value}. Error: {e}")

    # Escape YAML problematic characters
    value = value.replace("\n", " ").strip()
    value = value.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return value


def format_section_to_table(content, section_name):
    """Format specific sections like Classes, Interfaces, Enums, or Namespaces into a markdown table."""
    heading_level = "###" if section_name == "Namespaces" else "##"

    # Match the section based on the heading level
    match = re.search(rf'{heading_level} {section_name}\n\n(.*?)(?=\n###|\n##|\Z)', content, re.DOTALL)
    if match:
        section_content = match.group(1)
        section_content = replace_xref_tags_in_content(section_content)
        singular_name = {
            "Classes": "Class",
            "Namespaces": "Namespace",
            "Interfaces": "Interface",
            "Enums": "Enum"
        }.get(section_name, section_name[:-1])

        items = []

        # Handle Namespaces (No descriptions)
        if section_name == "Namespaces":
            item_blocks = re.findall(r'\[(.*?)\]\((.*?)\)', section_content)
            for name, link in item_blocks:
                cleaned_link = f"/{family}/{link.lower().replace('.md', '')}"
                items.append((name, cleaned_link, ""))  # No description for Namespaces

        # Handle other sections with descriptions
        else:
            item_blocks = re.findall(r'\[(.*?)\]\((.*?)\)(?:\s*\n\s*(.*?))?(?=\n\s*\[|\n###|\Z)', section_content, re.DOTALL)
            for name, link, desc in item_blocks:
                cleaned_link = f"/{family}/{link.lower().replace('.md', '')}"
                description = desc.strip().replace("\n", " ") if desc else ""  # Empty if no description
                items.append((name, cleaned_link, description))

        # Generate the markdown table
        table = f'## {section_name}\n\n| {singular_name} Name | Description |\n| --- | --- |\n'
        for name, link, description in items:
            table += f'| [{name}]({link}) | {description} |\n'

        # Replace the matched section with the formatted table
        content = content.replace(match.group(0), table)

    return content


def format_examples(content):
    """Fix 'Examples' section with proper closing of C# and Visual Basic code blocks."""
    
    # Case 1: Handle both C# and Visual Basic code blocks
    content = re.sub(
        r'<pre><code class="lang-csharp">\[C#\](.*?)\[Visual Basic\](.*?)</code></pre>',
        lambda m: f'```csharp\n{m.group(1).strip()}\n```\n```vb\n{m.group(2).strip()}\n```',
        content, flags=re.DOTALL
    )

    # Case 2: Multiline C# code block without Visual Basic mention
    content = re.sub(
        r'<example><pre><code class="lang-csharp">(.*?)</code></pre></example>',
        lambda m: f'```csharp\n{m.group(1).strip()}\n```',
        content, flags=re.DOTALL
    )

    # Case 3: Single-line code block (both tags on the same line)
    content = re.sub(
        r'<pre><code class="lang-csharp">(.*?)</code></pre>',
        lambda m: f'`{m.group(1).strip()}`' if '\n' not in m.group(1) else f'`{m.group(1).strip()}`',
        content
    )

    #Case 4: Multi-line code block
    content = re.sub(
    r'<pre><code class="lang-csharp">(.*?)</code></pre>',
    lambda m: f'`{m.group(1).strip()}`' if '\n' not in m.group(1) else f'```\ncsharp\n{m.group(1).strip()}\n```',
    content,
    flags=re.DOTALL  # Enables multi-line matching
    )

    def process_example_block(match):
        # Extract content inside <example>
        description = match.group(1).strip()
        code = match.group(2).strip()
        
        # Convert to a properly formatted markdown block
        formatted_block = f"{description}\n\n```csharp\n{code}\n```"
        return formatted_block

    # Match the <example> block with a description followed by a code block
    content = re.sub(
        r'<example>\s*(.*?)\s*<pre><code class="lang-csharp">(.*?)</code></pre>\s*</example>',
        process_example_block,
        content, flags=re.DOTALL
    )
    
    # remove </attachedfile> if within <pre> & </pre>
    content = re.sub(
    r'(<pre>.*?</pre>)',
    lambda m: re.sub(r'</attachedfile>', '', m.group(1), flags=re.DOTALL),
    content,
    flags=re.DOTALL
)
    
    # Remove any additional Visual Basic tags
    content = re.sub(r'\[Visual Basic\]\s*', '', content)
    content = re.sub(r'\[VB\.NET\]\s*', '', content)

    return content

def add_assembly_version(content):
    """Append version number to 'Assembly: FamilyName.dll' lines."""
    try:
        # Pattern to match 'Assembly: Aspose.Words.dll'
        pattern = rf'Assembly: {re.escape(family_name)}\.dll'
        replacement = f'Assembly: {family_name}.dll ({version})'

        # Replace occurrences in content
        content = re.sub(pattern, replacement, content)
    except Exception as e:
        print(f"Error adding assembly version: {e}")

    return content


def add_meta_info_to_file(file_path, layout_value):
    """Add YAML frontmatter, format content, and handle Namespace category files."""
    try:
        with open(file_path, 'r+', encoding='utf-8') as file:
            content = file.read()
            title, description, summary, category = extract_meta_info(content)

            # Remove the first line from the content
            content = '\n'.join(content.splitlines()[1:])

            if category == "Namespace":
                for section in ["Classes", "Interfaces", "Enums", "Namespaces"]:
                    content = format_section_to_table(content, section)

            # Format and clean content
            content = replace_xref_tags_in_content(content)
            content = format_examples(content)
            content = process_internal_links(content)
            content = add_assembly_version(content)  


            meta_info = f"""---
linkTitle: "{clean_yaml_field(title)}"
title: "{clean_yaml_field(title)}"
description: "{clean_yaml_field(description)}"
summary: "{clean_yaml_field(summary)}"
categories:
  - {category}
layout: "{layout_value}"
---"""

            # ✅ Write back changes without affecting other processing
            file.seek(0)
            file.write(meta_info + "\n" + content)
            file.truncate()
    except Exception as e:
        print(f"Error processing file {file_path}: {e}")

def update_frontmatter(content, layout_value):
    """Ensures YAML metadata includes the correct layout without duplication."""
    if content.startswith("---"):
        end_index = content.find("\n---", 3)
        if end_index == -1:
            print("Warning: Invalid YAML frontmatter detected.")
            return content

        yaml_section = content[:end_index + 4]  
        rest_of_content = content[end_index + 4:].strip()

        if "layout:" in yaml_section:
            yaml_section = re.sub(r'layout:\s*".*?"', f'layout: "{layout_value}"', yaml_section)
        else:
            yaml_section = yaml_section.rstrip() + f'\nlayout: "{layout_value}"\n'

        return yaml_section + "\n\n" + rest_of_content
    else:
        return f"---\nlayout: \"{layout_value}\"\n---\n\n{content}"


def rename_file():
    """Process all .md files first, then rename {family}.md to _index.md."""
    family_file = None
    expected_filename = f"{family_name}.md"  # Expected filename based on argument

    # ✅ First, process all .md files (without renaming yet)
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        if filename == expected_filename:  # Match ONLY the passed family name
            family_file = filename  # Store the correct file to rename later
        elif filename.endswith('.md'):
            add_meta_info_to_file(file_path, "reference-single")  # Process all other .md files normally

    # ✅ Now rename {family}.md (e.g., Aspose.Words.md) to _index.md
    if family_file:
        old_file_path = os.path.join(folder_path, family_file)
        new_file_path = os.path.join(folder_path, "_index.md")

        if os.path.exists(new_file_path):
            os.remove(new_file_path)
            print(f'Removed existing "{new_file_path}".')

        os.rename(old_file_path, new_file_path)
        print(f'Renamed "{old_file_path}" to "{new_file_path}".')

        # ✅ Apply layout: "reference-home" to _index.md
        add_meta_info_to_file(new_file_path, "reference-home")

# Execute renaming and processing for all markdown files
rename_file()

print("YAML frontmatter added, content formatted, and files processed successfully.")
