import type { GenerationJobState } from "@/entities/generation-job/model/types";
import { request } from "@/shared/api/base";

export interface GenerationGateway {
  getStatus(jobId: string): Promise<GenerationJobState>;
  refreshQueue(jobId: string): Promise<GenerationJobState>;
}

class HttpGenerationGateway implements GenerationGateway {
  async getStatus(jobId: string): Promise<GenerationJobState> {
    return request<GenerationJobState>(`/generation-jobs/${jobId}`);
  }

  async refreshQueue(jobId: string): Promise<GenerationJobState> {
    return request<GenerationJobState>(`/generation-jobs/${jobId}/refresh-queue`, {
      method: "POST",
    });
  }
}

export const generationGateway: GenerationGateway = new HttpGenerationGateway();
