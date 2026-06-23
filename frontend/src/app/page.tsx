export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-center px-6">
        <h1 className="text-4xl font-bold tracking-tight">DeepWiki</h1>
        <p className="mt-2 text-muted-foreground text-lg">
          AI-powered documentation for any GitHub repo
        </p>
      </main>
    </div>
  );
}
