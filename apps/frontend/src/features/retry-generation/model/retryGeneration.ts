import type { GenerationJobState } from "@/entities/generation-job/model/types";
import { generationGateway, type GenerationGateway } from "@/shared/api/gateways/generationGateway";

export async function retryGeneration(
  jobId: string,
  gateway: GenerationGateway = generationGateway
): Promise<GenerationJobState> {
  return gateway.refreshQueue(jobId);
}
