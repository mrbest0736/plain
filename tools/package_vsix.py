"""Package the Plain editor extension as an installable .vsix.

A .vsix is a zip with a manifest at the root.  This script builds it with the
Python standard library only, so no Node toolchain is required.

Run from the project root:  python3 tools/package_vsix.py
"""

import json
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXTENSION_DIR = os.path.join(ROOT, "editors", "plain-vscode")
DIST_DIR = os.path.join(ROOT, "dist")
ICON_PATH = os.path.join(EXTENSION_DIR, "icon.png")


def ensure_icon():
    """The icon is a generated file; rebuild it if it is missing."""
    if os.path.exists(ICON_PATH):
        return
    import make_logo

    make_logo.draw_png(ICON_PATH)
    print("generated", ICON_PATH)

COPY_TYPES = {
    "json": "application/json",
    "vsixmanifest": "text/xml",
    "xml": "text/xml",
    "png": "image/png",
    "svg": "image/svg+xml",
    "js": "application/javascript",
    "md": "text/markdown",
    "tmLanguage": "text/xml",
    "LICENSE": "text/plain",
}

VSIX_MANIFEST = """<?xml version="1.0" encoding="utf-8"?>
<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011" xmlns:d="http://schemas.microsoft.com/developer/vsx-schema-design/2011">
  <Metadata>
    <Identity Language="en-US" Id="plain-language" Version="{version}" Publisher="plain-lang"/>
    <DisplayName>Plain Language</DisplayName>
    <Description xml:space="preserve">Plain (.pln) is a programming language written almost entirely in English words. This extension adds syntax highlighting, snippets, live friendly diagnostics and one-command running to VS Code and Cursor.</Description>
    <Tags>plain,pln,english,beginner,education,language</Tags>
    <Categories>Programming Languages,Snippets</Categories>
    <GalleryFlags>Public</GalleryFlags>
    <Properties>
      <Property Id="Microsoft.VisualStudio.Code.Engine" Value="^1.70.0"/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionDependencies" Value=""/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionPack" Value=""/>
      <Property Id="Microsoft.VisualStudio.Code.ExtensionKind" Value="workspace"/>
      <Property Id="Microsoft.VisualStudio.Code.LocalizedLanguages" Value=""/>
    </Properties>
  </Metadata>
  <Installation>
    <InstallationTarget Id="Microsoft.VisualStudio.Code"/>
  </Installation>
  <Dependencies/>
  <Assets>
    <Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.Details" Path="extension/README.md" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="extension/LICENSE" Addressable="true"/>
    <Asset Type="Microsoft.VisualStudio.Services.Icons.Default" Path="extension/icon.png" Addressable="true"/>
  </Assets>
</PackageManifest>
"""

CONTENT_TYPES = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
{defaults}
</Types>
"""


def content_types_xml(extensions):
    seen = []
    for extension in extensions:
        if extension not in seen:
            seen.append(extension)
    lines = []
    for extension in seen:
        content_type = COPY_TYPES.get(extension, "application/octet-stream")
        lines.append('  <Default Extension="%s" ContentType="%s"/>' % (extension, content_type))
    return CONTENT_TYPES.format(defaults="\n".join(lines))


def main():
    ensure_icon()
    package_path = os.path.join(EXTENSION_DIR, "package.json")
    with open(package_path, "r", encoding="utf-8") as handle:
        package = json.load(handle)
    version = package["version"]
    out_path = os.path.join(DIST_DIR, "plain-language-%s.vsix" % version)
    os.makedirs(DIST_DIR, exist_ok=True)

    included = []
    for base, _dirs, files in os.walk(EXTENSION_DIR):
        for name in files:
            full = os.path.join(base, name)
            relative = os.path.relpath(full, EXTENSION_DIR)
            included.append((full, "extension/" + relative.replace(os.sep, "/")))

    extensions = set()
    for _full, archive_name in included:
        name = archive_name.rsplit("/", 1)[-1]
        if name == "LICENSE":
            extensions.add("LICENSE")
        elif "." in name:
            extensions.add(name.rsplit(".", 1)[-1].lower())

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("extension.vsixmanifest",
                         VSIX_MANIFEST.format(version=version))
        archive.writestr("[Content_Types].xml", content_types_xml(extensions))
        for full, archive_name in included:
            archive.write(full, archive_name)

    print("wrote", out_path)
    print("files:")
    with zipfile.ZipFile(out_path) as archive:
        for name in archive.namelist():
            print("  ", name)


if __name__ == "__main__":
    main()
