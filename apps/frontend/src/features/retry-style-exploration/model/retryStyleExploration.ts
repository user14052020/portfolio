import type { GenerationJobState } from "@/entities/generation-job/model/types";
import { retryGeneration } from "@/features/retry-generation/model/retryGeneration";

export async function retryStyleExploration(jobId: string): Promise<GenerationJobState> {
  return retryGeneration(jobId);
}
