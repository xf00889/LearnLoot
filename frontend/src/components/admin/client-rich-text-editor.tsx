"use client";

import dynamic from "next/dynamic";
import type { RichTextEditorProps } from "./rich-text-editor";

const Editor = dynamic(() => import("./rich-text-editor"), { ssr: false, loading: () => <div style={{ minHeight: 320, border: "1px solid #aaa", padding: 16 }}>Loading editor...</div> });
export default function ClientRichTextEditor(props: RichTextEditorProps) { return <Editor {...props} />; }
