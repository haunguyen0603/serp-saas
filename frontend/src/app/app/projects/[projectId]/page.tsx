import { ProjectDetail } from "@/features/projects/project-detail";

export default async function ProjectPage({
  params,
}: {
  params: Promise<{ projectId: string }>;
}) {
  const { projectId } = await params;
  return <ProjectDetail projectId={projectId} />;
}
