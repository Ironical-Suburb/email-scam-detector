import React from 'react';
import {View, Text, StyleSheet} from 'react-native';

type Props = {
  scamType: string;
  steps: string[];
};

export default function ProtocolCard({scamType, steps}: Props) {
  if (steps.length === 0) return null;

  return (
    <View style={styles.card}>
      <Text style={styles.title}>What to do right now</Text>
      {steps.map((step, idx) => (
        <View key={idx} style={styles.stepRow}>
          <View style={styles.numCircle}>
            <Text style={styles.numText}>{idx + 1}</Text>
          </View>
          <Text style={styles.stepText}>{step}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    padding: 16,
    marginTop: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: '#1a1a2e',
    marginBottom: 14,
  },
  stepRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  numCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#e74c3c',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
    marginTop: 1,
  },
  numText: {
    color: '#fff',
    fontWeight: '700',
    fontSize: 14,
  },
  stepText: {
    flex: 1,
    fontSize: 16,
    color: '#333',
    lineHeight: 22,
  },
});
