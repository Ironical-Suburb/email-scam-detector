import React from 'react';
import {View, Text, TouchableOpacity, StyleSheet} from 'react-native';

type Props = {
  riskLabel: 'flagged' | 'review';
  riskScore: number;
  scamType: string | null;
  onSharePress: () => void;
};

const SCAM_TYPE_DISPLAY: Record<string, string> = {
  irs_impersonation: 'IRS Impersonation',
  tech_support: 'Tech Support Scam',
  lottery_prize: 'Lottery / Prize Scam',
  bank_fraud: 'Bank Fraud',
  romance_scam: 'Romance Scam',
  package_delivery: 'Fake Package Delivery',
  grandparent_scam: 'Grandparent Scam',
};

export default function ScamBanner({riskLabel, riskScore, scamType, onSharePress}: Props) {
  const isFlagged = riskLabel === 'flagged';
  const bgColor = isFlagged ? '#e74c3c' : '#f39c12';
  const headline = isFlagged
    ? 'This email looks like a scam.'
    : 'This email might be suspicious.';

  return (
    <View style={[styles.banner, {backgroundColor: bgColor}]}>
      <Text style={styles.headline}>{headline}</Text>

      {scamType && (
        <Text style={styles.type}>
          Type: {SCAM_TYPE_DISPLAY[scamType] ?? scamType}
        </Text>
      )}

      <Text style={styles.score}>Risk score: {riskScore}%</Text>

      <TouchableOpacity style={styles.shareBtn} onPress={onSharePress}>
        <Text style={styles.shareBtnText}>Tell a family member</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    padding: 20,
    marginBottom: 8,
  },
  headline: {
    fontSize: 22,
    fontWeight: '800',
    color: '#ffffff',
    marginBottom: 6,
  },
  type: {
    fontSize: 16,
    color: 'rgba(255,255,255,0.9)',
    marginBottom: 4,
  },
  score: {
    fontSize: 14,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 16,
  },
  shareBtn: {
    backgroundColor: 'rgba(0,0,0,0.25)',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    alignSelf: 'flex-start',
  },
  shareBtnText: {
    color: '#ffffff',
    fontSize: 15,
    fontWeight: '700',
  },
});
