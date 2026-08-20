import React from "react";
import { StyleSheet, Text, View } from "react-native";
import Svg, { Circle } from "react-native-svg";
import { color, type } from "@/theme/tokens";

interface Props {
  score: number; // 0-100
  size?: number;
  strokeWidth?: number;
  accent?: string;
  sublabel?: string;
}

// Signature element: a single decisive ring, like a line-call indicator,
// rather than a generic dashboard gauge. Sweep is a fixed 270° arc (not a
// full circle) so it reads as an instrument dial, not a pie chart.
export function ScoreRing({ score, size = 160, strokeWidth = 12, accent = color.accent, sublabel }: Props) {
  const clamped = Math.max(0, Math.min(100, score));
  const radiusPx = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radiusPx;
  const arcFraction = 0.75; // 270 degrees of the circle is the visible track
  const trackLength = circumference * arcFraction;
  const progressLength = trackLength * (clamped / 100);
  const rotation = 135; // start angle so the gap sits at the bottom

  return (
    <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Svg width={size} height={size} style={{ position: "absolute", transform: [{ rotate: `${rotation}deg` }] }}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radiusPx}
          stroke={color.line}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={`${trackLength} ${circumference}`}
          strokeLinecap="round"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radiusPx}
          stroke={accent}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={`${progressLength} ${circumference}`}
          strokeLinecap="round"
        />
      </Svg>
      <Text style={styles.score}>{Math.round(clamped)}</Text>
      {sublabel ? <Text style={styles.sublabel}>{sublabel}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  score: { ...type.scoreHuge, color: color.ink },
  sublabel: { ...type.small, color: color.inkMuted, marginTop: -4 },
});
