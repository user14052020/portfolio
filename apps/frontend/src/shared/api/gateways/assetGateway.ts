import { request } from "@/shared/api/base";
import type { UploadedAsset } from "@/shared/api/types";

export interface AssetGateway {
  uploadGarmentAsset(file: File): Promise<UploadedAsset>;
}

class HttpAssetGateway implements AssetGateway {
  async uploadGarmentAsset(file: File): Promise<UploadedAsset> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("related_entity", "generation_input");
    const response = await request<{ asset: UploadedAsset }>("/uploads", {
      method: "POST",
      body: formData,
    });
    return response.asset;
  }
}

export const assetGateway: AssetGateway = new HttpAssetGateway();
