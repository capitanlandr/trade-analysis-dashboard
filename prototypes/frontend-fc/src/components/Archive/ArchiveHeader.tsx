interface ArchiveHeaderProps {
  title: string;
  description: string;
}

export function ArchiveHeader({ title, description }: ArchiveHeaderProps) {
  return (
    <div>
      <h1 className="text-3xl font-bold text-gray-900">{title}</h1>
      <p className="text-gray-600 mt-2">{description}</p>
    </div>
  );
}
