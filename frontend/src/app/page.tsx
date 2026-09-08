import { getHealth } from "@/lib/api";

export default async function Home() {
  const health = await getHealth();

  return (
    <main className="flex min-h-screen items-center justify-center">
      <div className="rounded-xl border p-8">
        <h1 className="text-2xl font-semibold">Course Deals</h1>

        <p className="mt-4">
          Backend: {health.status}
        </p>

        <p>
          Database: {health.database}
        </p>
      </div>
    </main>
  );
}
