import React from "react";
import { StyleSheet, Text, View } from "react-native";
import { Fault } from "@/api/types";
import { color, radius, space, type } from "@/theme/tokens";
import { formatFaultCode } from "@/utils/format";

// Freedom-to-Play: hard faults are called, soft deviations are logged, never
// penalized. The visual language has to carry that distinction on sight —
// hard gets a filled left rule + red, soft gets a hollow rule + amber, and
// the copy itself never says "wrong" for a soft entry.
export function FaultCard({ fault }: { fault: Fault }) {
  const isHard = fault.type === "hard";
  const accentColor = isHard ? color.hardFault : color.softFault;
  return (
    <View style={[styles.wrap, { borderLeftColor: accentColor }]}>
      <View style={styles.headerRow}>
        <Text style={[styles.kind, { color: accentColor }]}>
          {isHard ? "HARD FAULT" : "STYLE NOTE"}
        </Text>
        <Text style={styles.frame}>Frame {fault.frame}</Text>
      </View>
      <Text style={styles.code}>{formatFaultCode(fault.faultCode)}</Text>
      <Text style={styles.description}>{fault.description}</Text>
      {fault.referenceSource ? (
        <Text style={styles.reference}>Source: {fault.referenceSource}</Text>
      ) : isHard ? (
        <Text style={styles.referencePending}>Reference threshold pending — provisional call</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: color.bgElevated,
    borderRadius: radius.md,
    borderLeftWidth: 3,
    padding: space.lg,
    gap: 6,
  },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  kind: { ...type.label },
  frame: { ...type.small, color: color.inkFaint },
  code: { ...type.h3, color: color.ink },
  description: { ...type.body, color: color.inkMuted },
  reference: { ...type.small, color: color.inkFaint, marginTop: 2 },
  referencePending: { ...type.small, color: color.softFault, marginTop: 2 },
});
