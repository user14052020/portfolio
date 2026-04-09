import { assetGateway, type AssetGateway } from "@/shared/api/gateways/assetGateway";
import type { UploadedAsset } from "@/shared/api/types";

export async function attachGarmentAsset(
  file: File,
  gateway: AssetGateway = assetGateway
): Promise<UploadedAsset> {
  return gateway.uploadGarmentAsset(file);
}
