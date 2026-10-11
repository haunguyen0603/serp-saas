import "../globals.css";
import { RootDocument } from "@/components/root-document";
export { metadata } from "@/components/root-document";
export default function EnglishLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <RootDocument>{children}</RootDocument>;
}
