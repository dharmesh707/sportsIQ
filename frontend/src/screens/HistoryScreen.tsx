import React, { useCallback, useEffect, useState } from "react";
import { FlatList, Pressable, StyleSheet, Text, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { SafeAreaView } from "react-native-safe-area-context";
import { api } from "@/api/client";
import { ApiError, AnalysisResultSummary, SportType } from "@/api/types";
import { RootStackParamList } from "@/navigation/types";
import { Card } from "@/components/Primitives";
import { ErrorBanner } from "@/components/ErrorBanner";
import { EmptyState } from "@/components/EmptyState";
import { LoadingState } from "@/components/LoadingState";
import { SportBadge } from "@/components/SportBadge";
import { color, radius, space, type } from "@/theme/tokens";
import { SPORT_OPTIONS } from "@/utils/sportMeta";
import { formatActionLabel, formatDateTime } from "@/utils/format";

type Nav = NativeStackNavigationProp<RootStackParamList>;

export default function HistoryScreen() {
  const navigation = useNavigation<Nav>();
  const [sportFilter, setSportFilter] = useState<SportType | null>(null);
  const [items, setItems] = useState<AnalysisResultSummary[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(
    async (targetPage: number, replace: boolean) => {
      if (targetPage === 1) setLoading(true);
      else setLoadingMore(true);
      setError(null);
      try {
        const res = await api.history({
          page: targetPage,
          pageSize: 20,
          sportType: sportFilter ?? undefined,
        });
        setItems((prev) => (replace ? res.analyses : [...prev, ...res.analyses]));
        setPage(res.pagination.page);
        setTotalPages(res.pagination.totalPages);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Couldn't load history.");
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [sportFilter]
  );

  useEffect(() => {
    load(1, true);
  }, [load]);

  const loadMore = () => {
    if (loadingMore || page >= totalPages) return;
    load(page + 1, false);
  };

  return (
    <SafeAreaView style={styles.safe} edges={["top"]}>
      <View style={styles.headerBlock}>
        <Text style={styles.title}>History</Text>
        <FlatList
          horizontal
          showsHorizontalScrollIndicator={false}
          data={[{ value: null, label: "All" }, ...SPORT_OPTIONS]}
          keyExtractor={(item) => item.value ?? "all"}
          contentContainerStyle={{ gap: space.sm }}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => setSportFilter(item.value)}
              style={[styles.filterChip, sportFilter === item.value && styles.filterChipActive]}
            >
              <Text
                style={[
                  styles.filterChipText,
                  sportFilter === item.value && styles.filterChipTextActive,
                ]}
              >
                {item.label}
              </Text>
            </Pressable>
          )}
        />
      </View>

      {loading ? (
        <LoadingState label="Loading history…" />
      ) : error ? (
        <View style={styles.padded}>
          <ErrorBanner message={error} onRetry={() => load(1, true)} />
        </View>
      ) : items.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          body={
            sportFilter
              ? "You haven't analyzed a clip for this sport yet."
              : "Analyze your first clip to start building history."
          }
        />
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item) => item.analysisId}
          contentContainerStyle={styles.padded}
          onEndReachedThreshold={0.4}
          onEndReached={loadMore}
          ListFooterComponent={loadingMore ? <LoadingState label="Loading more…" /> : null}
          renderItem={({ item }) => (
            <Pressable
              onPress={() => navigation.navigate("AnalysisDetail", { analysisId: item.analysisId })}
            >
              <Card style={styles.row}>
                <View style={styles.rowTop}>
                  <SportBadge sportType={item.sportType} />
                  <Text style={styles.score}>{Math.round(item.overallScore)}</Text>
                </View>
                <Text style={styles.actionLabel}>{formatActionLabel(item.actionLabel)}</Text>
                <View style={styles.rowBottom}>
                  <Text style={styles.faultCounts}>
                    {item.hardFaultCount} hard · {item.softFaultCount} soft
                  </Text>
                  <Text style={styles.date}>{formatDateTime(item.createdAt)}</Text>
                </View>
              </Card>
            </Pressable>
          )}
        />
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: color.bg },
  headerBlock: { paddingHorizontal: space.lg, paddingTop: space.md, gap: space.md },
  title: { ...type.h1, color: color.ink },
  padded: { padding: space.lg, gap: space.md },
  filterChip: {
    borderWidth: 1,
    borderColor: color.line,
    borderRadius: radius.pill,
    paddingVertical: space.sm,
    paddingHorizontal: space.md,
  },
  filterChipActive: { backgroundColor: color.accent, borderColor: color.accent },
  filterChipText: { ...type.smallMedium, color: color.inkMuted },
  filterChipTextActive: { color: color.accentInk },
  row: { gap: 6 },
  rowTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  score: { ...type.h2, color: color.ink },
  actionLabel: { ...type.h3, color: color.ink },
  rowBottom: { flexDirection: "row", justifyContent: "space-between" },
  faultCounts: { ...type.small, color: color.inkMuted },
  date: { ...type.small, color: color.inkFaint },
});
