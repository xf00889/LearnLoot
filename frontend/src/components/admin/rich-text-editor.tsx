"use client";

import { CKEditor } from "@ckeditor/ckeditor5-react";
import {
  Alignment, Autoformat, BlockQuote, Bold, ClassicEditor, CodeBlock, Essentials, FindAndReplace,
  Heading, HorizontalLine, Image, ImageCaption, ImageResize, ImageStyle, ImageToolbar, ImageUpload,
  Indent, IndentBlock, Italic, Link, List, Paragraph, PasteFromOffice, RemoveFormat, SimpleUploadAdapter,
  SourceEditing, SpecialCharacters, SpecialCharactersEssentials, Table, TableToolbar, Underline, WordCount,
} from "ckeditor5";
import "ckeditor5/ckeditor5.css";
import { adminMediaUploadUrl, currentCsrfToken } from "@/lib/admin-api";

export type RichTextEditorProps = { value: string; onChange: (value: string) => void; minHeight?: number };

export default function RichTextEditor({ value, onChange, minHeight = 320 }: RichTextEditorProps) {
  const licenseKey = process.env.NEXT_PUBLIC_CKEDITOR_LICENSE_KEY?.trim() || "GPL";
  return (
    <div className="learnloot-editor" style={{ ["--editor-min-height" as string]: `${minHeight}px` }}>
      <CKEditor
        editor={ClassicEditor}
        data={value}
        config={{
          licenseKey,
          plugins: [Essentials, Paragraph, Heading, Bold, Italic, Underline, Link, List, BlockQuote, Alignment, Indent, IndentBlock, Table, TableToolbar, Image, ImageToolbar, ImageCaption, ImageStyle, ImageResize, ImageUpload, SimpleUploadAdapter, CodeBlock, HorizontalLine, SpecialCharacters, SpecialCharactersEssentials, FindAndReplace, RemoveFormat, SourceEditing, WordCount, PasteFromOffice, Autoformat],
          toolbar: { items: ["undo", "redo", "|", "heading", "|", "bold", "italic", "underline", "removeFormat", "|", "link", "bulletedList", "numberedList", "blockQuote", "|", "alignment", "outdent", "indent", "|", "insertTable", "uploadImage", "codeBlock", "horizontalLine", "specialCharacters", "|", "findAndReplace", "sourceEditing"] },
          image: { toolbar: ["imageTextAlternative", "toggleImageCaption", "imageStyle:inline", "imageStyle:block", "imageStyle:side", "resizeImage"] },
          table: { contentToolbar: ["tableColumn", "tableRow", "mergeTableCells"] },
          simpleUpload: { uploadUrl: adminMediaUploadUrl(), withCredentials: true, headers: () => ({ "X-CSRFToken": currentCsrfToken() }) },
        }}
        onChange={(_, editor) => onChange(editor.getData())}
      />
    </div>
  );
}
