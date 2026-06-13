import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import * as prospectsApi from "@/api/prospects";
import type { ProspectFilters } from "@/api/prospects";
import type { Prospect } from "@/types";

export const prospectKeys = {
  all: ["prospects"] as const,
  list: (filters: ProspectFilters) => ["prospects", "list", filters] as const,
  detail: (id: string) => ["prospects", "detail", id] as const,
};

export function useProspects(filters: ProspectFilters = {}) {
  return useQuery({
    queryKey: prospectKeys.list(filters),
    queryFn: () => prospectsApi.listProspects(filters),
    staleTime: 30_000,
  });
}

export function useProspect(id: string) {
  return useQuery({
    queryKey: prospectKeys.detail(id),
    queryFn: () => prospectsApi.getProspect(id),
    enabled: !!id,
  });
}

export function useCreateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: prospectsApi.createProspect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prospectKeys.all });
    },
  });
}

export function useUpdateProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Partial<Prospect> }) =>
      prospectsApi.updateProspect(id, payload),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: prospectKeys.all });
      queryClient.invalidateQueries({ queryKey: prospectKeys.detail(id) });
    },
  });
}

export function useDeleteProspect() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, hard }: { id: string; hard?: boolean }) =>
      prospectsApi.deleteProspect(id, hard),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: prospectKeys.all });
    },
  });
}
