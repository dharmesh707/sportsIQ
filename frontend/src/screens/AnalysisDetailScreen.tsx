import React, { useEffect, useState } from "react";
import { View } from "react-native";
import { NativeStackScreenProps } from "@react-navigation/native-stack";
import { api } from "@/api/client";
import { ApiError, AnalysisResult } from "@/api/types";
import { RootStackParamList } from "@/navigation/types";
import { Screen } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { LoadingState } from "@/components/LoadingState";
import { AnalysisResultView } from "@/components/AnalysisResultView";
import { space } from "@/theme/tokens";

type Props = NativeStackScreenProps<RootStackParamList, "AnalysisDetail">;

export default function AnalysisDetailScreen({ route }: Props) {
  const { analysisId } = route.params;
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.analysisById(analysisId);
      setResult(res);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Couldn't load this session.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [analysisId]);

  return (
    <Screen>
      {loading ? (
        <LoadingState label="Loading session…" />
      ) : error ? (
        <ErrorBanner message={error} onRetry={load} />
      ) : result ? (
        <View style={{ gap: space.lg }}>
          <AnalysisResultView result={result} />
        </View>
      ) : null}
    </Screen>
  );
}
