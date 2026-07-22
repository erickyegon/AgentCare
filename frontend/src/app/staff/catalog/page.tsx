"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { Department } from "@/lib/types";
import { Button, Card, CardHeader, EmptyState, Input, SkeletonRows } from "@/components/ui";

export default function CatalogPage() {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [keywords, setKeywords] = useState("");

  const { data, isLoading } = useQuery({ queryKey: ["departments"], queryFn: () => api.get<Department[]>("/departments") });

  const create = useMutation({
    mutationFn: () => api.post<Department>("/departments", { name, description, keywords }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["departments"] });
      setName(""); setDescription(""); setKeywords("");
    },
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-2xl font-bold text-slate-900">Departments</h1>

      <Card>
        <CardHeader title="Add department" subtitle="Routing agent can only route to departments that exist here" />
        <div className="grid gap-3 p-5 sm:grid-cols-3">
          <Input placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input placeholder="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          <Input placeholder="Keywords (space-separated)" value={keywords} onChange={(e) => setKeywords(e.target.value)} />
          <Button className="sm:col-span-3 sm:w-40" loading={create.isPending} onClick={() => create.mutate()} disabled={!name}>
            Add department
          </Button>
        </div>
      </Card>

      <Card>
        <CardHeader title="Active departments" />
        <div className="p-3">
          {isLoading ? <SkeletonRows rows={4} /> : data && data.length > 0 ? (
            <div className="grid gap-2 p-2 sm:grid-cols-2">
              {data.map((d) => (
                <div key={d.id} className="rounded-lg border border-slate-200 p-3">
                  <p className="font-medium text-slate-800">{d.name}</p>
                  <p className="text-xs text-slate-500">{d.description}</p>
                </div>
              ))}
            </div>
          ) : <div className="p-4"><EmptyState title="No departments" /></div>}
        </div>
      </Card>
    </div>
  );
}
