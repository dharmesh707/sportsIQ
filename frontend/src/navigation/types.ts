import { SportType } from "@/api/types";

export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
};

export type MainTabParamList = {
  DashboardTab: undefined;
  AnalyzeTab: undefined;
  HistoryTab: undefined;
  ProgressTab: undefined;
  TrainTab: undefined;
  ProfileTab: undefined;
};

export type RootStackParamList = {
  Main: undefined;
  AnalysisResultScreen: { analysisId?: string; inline?: boolean };
  AnalysisDetail: { analysisId: string };
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}

export type { SportType };
