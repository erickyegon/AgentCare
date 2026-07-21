"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { api } from "@/lib/api";
import type { PatientDocument } from "@/lib/types";
import { Badge, Button, Card, CardHeader, EmptyState, Spinner } from "@/components/ui";
import { formatDateTime } from "@/lib/utils";
import { FileUp } from "lucide-react";

export default function DocumentsPage() {
  const qc = useQueryClient();
  const fileRef = useRef<HTMLInputElement>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["my-documents"],
    queryFn: () => api.get<PatientDocument[]>("/me/documents"),
  });
  const upload = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("file", file);
      return api.upload<PatientDocument>("/me/documents", form);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["my-documents"] }),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">My documents</h1>
        <Button loading={upload.isPending} onClick={() => fileRef.current?.click()}>
          <FileUp className="h-4 w-4" /> Upload document
        </Button>
        <input ref={fileRef} type="file" className="hidden" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload.mutate(f); e.target.value = ""; }} />
      </div>

      <Card>
        <CardHeader title="Documents" subtitle="Classified and de-duplicated by the Document agent" />
        <div className="p-3">
          {isLoading ? (
            <div className="p-4"><Spinner /></div>
          ) : data && data.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {data.map((d) => (
                <div key={d.id} className="flex items-center justify-between gap-4 px-3 py-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-700">{d.original_filename}</p>
                    <p className="text-xs text-slate-400">
                      {(d.size_bytes / 1024).toFixed(1)} KB · {formatDateTime(d.created_at)} · sha256 {d.checksum.slice(0, 10)}…
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge label={d.document_type} />
                    <span className="text-xs text-slate-400">{Math.round(d.classification_confidence * 100)}%</span>
                    {d.is_duplicate && <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs text-amber-700">duplicate</span>}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-4"><EmptyState title="No documents yet" hint="Upload an ECG, blood report, or referral." /></div>
          )}
        </div>
      </Card>
    </div>
  );
}
