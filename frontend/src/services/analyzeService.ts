import { apiClient } from '../api/client';
import { SportType } from '../constants/sports';
import { AnalysisResult, HistoryResponse } from '../types/api';

/**
 * videoUri: local file URI from expo-camera / expo-image-picker (e.g.
 * "file:///.../clip.mp4"). Contract expects multipart form-data with a
 * `video` file field and a `sportType` form field — see API_CONTRACT.md.
 */
export async function analyzeVideo(
  videoUri: string,
  sportType: SportType
): Promise<AnalysisResult> {
  const formData = new FormData();
  // React Native's FormData accepts this object shape for file uploads —
  // it is NOT a standard web File/Blob, this is the RN-specific pattern.
  formData.append('video', {
    uri: videoUri,
    name: 'clip.mp4',
    type: 'video/mp4',
  } as unknown as Blob);
  formData.append('sportType', sportType);

  const { data } = await apiClient.post<AnalysisResult>('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function getHistory(): Promise<HistoryResponse> {
  const { data } = await apiClient.get<HistoryResponse>('/history');
  return data;
}
