import React, { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import { Video, ResizeMode } from "expo-av";
import { api } from "@/api/client";
import { ApiError, AnalysisResult, SportSupportInfo, SportType } from "@/api/types";
import { messageFor } from "@/utils/errorMessages";
import { Screen, Card, PrimaryButton, SecondaryButton, SectionLabel } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { LoadingState } from "@/components/LoadingState";
import { AnalysisResultView } from "@/components/AnalysisResultView";
import { SportPicker } from "@/components/SportPicker";
import { color, radius, space, type } from "@/theme/tokens";

type Stage = "idle" | "uploading" | "done" | "error";



export default function AnalyzeScreen() {
  const [sportType, setSportType] = useState<SportType>("badminton");
  const [sportSupport, setSportSupport] = useState<SportSupportInfo[] | null>(null);
  const [video, setVideo] = useState<{ uri: string; name: string; type: string } | null>(null);
  const [stage, setStage] = useState<Stage>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Best-effort: if this fails, every sport chip just renders without a
    // COMING SOON badge - selection and upload still work either way.
    api
      .sports()
      .then((res) => {
        if (!cancelled) setSportSupport(res.sports);
      })
      .catch(() => {
        if (!cancelled) setSportSupport(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const currentSupport = sportSupport?.find((s) => s.sportType === sportType);
  const isPreviewSport = currentSupport?.status === "PREVIEW";

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
      // The UI must never sit on a loading screen indefinitely: every path
      // through this catch always lands on the "error" stage with a Retry
      // button, whether the failure was a 4xx, a 5xx, a timeout, a dropped
      // connection, or a response that wasn't valid JSON at all.
      setErrorMessage(e instanceof ApiError ? messageFor(e) : "Couldn't analyze that clip.");
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
            <SportPicker value={sportType} onChange={setSportType} support={sportSupport} />
          </View>

          {isPreviewSport ? (
            <View style={styles.previewNotice}>
              <Text style={styles.previewNoticeText}>
                {currentSupport?.note ??
                  "This sport isn't implemented yet - uploads return placeholder numbers, not a real analysis of your video."}
              </Text>
            </View>
          ) : null}

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

          {stage === "error" && errorMessage ? (
            <ErrorBanner message={errorMessage} onRetry={video ? runAnalysis : undefined} />
          ) : errorMessage ? (
            <ErrorBanner message={errorMessage} />
          ) : null}

          {stage === "uploading" ? (
            <View style={{ gap: space.sm }}>
              <LoadingState label="Analyzing your form\u2026" />
              <Text style={styles.uploadingHint}>
                This can take up to a minute - pose tracking runs on the full clip.
              </Text>
            </View>
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
  previewNotice: {
    backgroundColor: color.bgElevated2,
    borderRadius: radius.md,
    padding: space.md,
    borderWidth: 1,
    borderColor: color.line,
  },
  previewNoticeText: { ...type.small, color: color.inkMuted },
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
  uploadingHint: { ...type.small, color: color.inkFaint, textAlign: "center" },
});
