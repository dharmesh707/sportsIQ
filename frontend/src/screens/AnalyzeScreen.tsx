import React, { useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Video, ResizeMode } from "expo-av";
import { api } from "@/api/client";
import { ApiError, AnalysisResult, SportType } from "@/api/types";
import { Screen, Card, PrimaryButton, SectionLabel } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { LoadingState } from "@/components/LoadingState";
import { AnalysisResultView } from "@/components/AnalysisResultView";
import { color, radius, space, type } from "@/theme/tokens";
import { SPORT_OPTIONS } from "@/utils/sportMeta";

type Stage = "idle" | "uploading" | "done" | "error";

export default function AnalyzeScreen() {
  const [sportType, setSportType] = useState<SportType>("badminton");
  const [video, setVideo] = useState<{ uri: string; name: string; type: string } | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  const pickVideo = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setErrorMessage("Allow access to your video library to upload a clip.");
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Videos,
      quality: 1,
    });
    if (picked.canceled || !picked.assets?.[0]) return;
    const asset = picked.assets[0];
    setVideo({
      uri: asset.uri,
      name: asset.fileName ?? "clip.mp4",
      type: asset.mimeType ?? "video/mp4",
    });
    setResult(null);
    setStage("idle");
    setErrorMessage(null);
  };

  const runAnalysis = async () => {
    if (!video) return;
    setStage("uploading");
    setErrorMessage(null);
    try {
      const res = await api.analyze(video, sportType);
      setResult(res);
      setStage("done");
    } catch (e) {
      setErrorMessage(e instanceof ApiError ? e.message : "Couldn't analyze that clip.");
      setStage("error");
    }
  };

  const reset = () => {
    setVideo(null);
    setResult(null);
    setStage("idle");
    setErrorMessage(null);
  };

  return (
    <Screen>
      <View>
        <Text style={styles.title}>Analyze</Text>
        <Text style={styles.subtitle}>Upload a clip, pick the sport, get scored.</Text>
      </View>

      {!result && (
        <>
          <View>
            <SectionLabel>SPORT</SectionLabel>
            <View style={styles.sportRow}>
              {SPORT_OPTIONS.map((opt) => (
                <Pressable
                  key={opt.value}
                  onPress={() => setSportType(opt.value)}
                  style={[
                    styles.sportChip,
                    sportType === opt.value && styles.sportChipActive,
                  ]}
                >
                  <Text
                    style={[
                      styles.sportChipText,
                      sportType === opt.value && styles.sportChipTextActive,
                    ]}
                  >
                    {opt.label}
                  </Text>
                </Pressable>
              ))}
            </View>
          </View>

          <Card>
            {video ? (
              <View style={styles.videoWrap}>
                <Video
                  source={{ uri: video.uri }}
                  style={styles.video}
                  useNativeControls
                  resizeMode={ResizeMode.CONTAIN}
                  isLooping
                />
              </View>
            ) : (
              <Pressable onPress={pickVideo} style={styles.uploadTarget}>
                <Text style={styles.uploadIcon}>+</Text>
                <Text style={styles.uploadText}>Select a video clip</Text>
              </Pressable>
            )}
            {video ? (
              <Pressable onPress={pickVideo}>
                <Text style={styles.changeClip}>Choose a different clip</Text>
              </Pressable>
            ) : null}
          </Card>

          {errorMessage ? <ErrorBanner message={errorMessage} onRetry={video ? runAnalysis : undefined} /> : null}

          {stage === "uploading" ? (
            <LoadingState label="Analyzing your form…" />
          ) : (
            <PrimaryButton label="Run analysis" onPress={runAnalysis} disabled={!video} />
          )}
        </>
      )}

      {result && (
        <View style={{ gap: space.lg }}>
          <AnalysisResultView result={result} />
          <PrimaryButton label="Analyze another clip" onPress={reset} />
        </View>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { ...type.h1, color: color.ink },
  subtitle: { ...type.body, color: color.inkMuted, marginTop: 2 },
  sportRow: { flexDirection: "row", flexWrap: "wrap", gap: space.sm },
  sportChip: {
    borderWidth: 1,
    borderColor: color.line,
    borderRadius: radius.pill,
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
  },
  sportChipActive: { backgroundColor: color.accent, borderColor: color.accent },
  sportChipText: { ...type.smallMedium, color: color.inkMuted },
  sportChipTextActive: { color: color.accentInk },
  uploadTarget: {
    height: 160,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: color.line,
    borderStyle: "dashed",
    alignItems: "center",
    justifyContent: "center",
    gap: space.sm,
  },
  uploadIcon: { ...type.h1, color: color.accent },
  uploadText: { ...type.body, color: color.inkMuted },
  videoWrap: { borderRadius: radius.md, overflow: "hidden" },
  video: { width: "100%", height: 220, backgroundColor: color.bg },
  changeClip: { ...type.smallMedium, color: color.accent, textAlign: "center", marginTop: space.sm },
  resultHeader: { gap: space.sm },
  actionLabel: { ...type.h2, color: color.ink },
  scoreCard: { alignItems: "center", paddingVertical: space.xl },
  comparison: { ...type.body, color: color.inkMuted, textAlign: "center", marginTop: space.sm },
  statGrid: { flexDirection: "row", flexWrap: "wrap", gap: space.lg },
  statCell: { width: "42%", gap: 2 },
  statValue: { ...type.h2, color: color.ink },
  statLabel: { ...type.small, color: color.inkFaint },
  listItem: { ...type.body, color: color.inkMuted, marginBottom: space.xs },
  listItemPositive: { ...type.body, color: color.positive, marginBottom: space.xs },
});
