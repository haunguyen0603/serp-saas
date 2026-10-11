import "../globals.css";
import { RootDocument } from "@/components/root-document";
export { metadata } from "@/components/root-document";
export default function VietnameseLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <RootDocument locale="vi">{children}</RootDocument>;
}
