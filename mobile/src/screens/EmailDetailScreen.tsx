import React, {useEffect, useState} from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
  Share,
} from 'react-native';
import {useRoute} from '@react-navigation/native';
import type {RouteProp} from '@react-navigation/native';
import type {RootStackParamList} from '../../App';
import ScamBanner from '../components/ScamBanner';
import ProtocolCard from '../components/ProtocolCard';
import {api} from '../api';

type Route = RouteProp<RootStackParamList, 'EmailDetail'>;

type EmailDetail = {
  id: string;
  subject: string;
  from: string;
  body_preview: string;
  risk_score: number;
  risk_label: 'flagged' | 'review' | 'clean';
  scam_type: string | null;
  protocol_steps: string[];
};

export default function EmailDetailScreen() {
  const route = useRoute<Route>();
  const {emailId} = route.params;
  const [detail, setDetail] = useState<EmailDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [feedbackSent, setFeedbackSent] = useState<boolean | null>(null);

  useEffect(() => {
    api.getEmailDetail(emailId).then(d => {
      setDetail(d);
      setLoading(false);
    });
  }, [emailId]);

  const submitFeedback = async (isScam: boolean) => {
    await api.submitFeedback(emailId, isScam);
    setFeedbackSent(isScam);
  };

  const shareWarning = async () => {
    if (!detail) return;
    await Share.share({
      message: `Heads up — I received an email that looks like a scam (${detail.scam_type ?? 'unknown type'}). Stay alert and do not respond to anything like it.`,
    });
  };

  if (loading || !detail) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#e74c3c" />
      </View>
    );
  }

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {detail.risk_label !== 'clean' && (
        <ScamBanner
          riskLabel={detail.risk_label}
          riskScore={detail.risk_score}
          scamType={detail.scam_type}
          onSharePress={shareWarning}
        />
      )}

      <View style={styles.meta}>
        <Text style={styles.metaLabel}>From</Text>
        <Text style={styles.metaValue}>{detail.from}</Text>
        <Text style={styles.metaLabel}>Subject</Text>
        <Text style={styles.metaValue}>{detail.subject}</Text>
      </View>

      <Text style={styles.bodyText}>{detail.body_preview}</Text>

      {detail.protocol_steps.length > 0 && (
        <ProtocolCard scamType={detail.scam_type ?? ''} steps={detail.protocol_steps} />
      )}

      {feedbackSent === null && detail.risk_label !== 'clean' && (
        <View style={styles.feedbackRow}>
          <Text style={styles.feedbackQuestion}>Was this flagged correctly?</Text>
          <View style={styles.feedbackButtons}>
            <Text style={styles.feedbackBtn} onPress={() => submitFeedback(true)}>
              Yes, it's a scam
            </Text>
            <Text style={[styles.feedbackBtn, styles.feedbackBtnNo]} onPress={() => submitFeedback(false)}>
              No, it's real
            </Text>
          </View>
        </View>
      )}

      {feedbackSent !== null && (
        <Text style={styles.feedbackThanks}>
          Thank you — your feedback helps us protect others.
        </Text>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#f5f5f5'},
  content: {paddingBottom: 40},
  center: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  meta: {backgroundColor: '#fff', padding: 16, marginBottom: 8},
  metaLabel: {fontSize: 11, color: '#888', textTransform: 'uppercase', marginTop: 8},
  metaValue: {fontSize: 15, color: '#1a1a2e', fontWeight: '500'},
  bodyText: {
    fontSize: 15,
    color: '#333',
    lineHeight: 22,
    backgroundColor: '#fff',
    padding: 16,
    marginBottom: 8,
  },
  feedbackRow: {backgroundColor: '#fff', padding: 16, marginTop: 8},
  feedbackQuestion: {fontSize: 16, fontWeight: '600', color: '#1a1a2e', marginBottom: 12},
  feedbackButtons: {flexDirection: 'row', gap: 12},
  feedbackBtn: {
    flex: 1,
    textAlign: 'center',
    backgroundColor: '#e74c3c',
    color: '#fff',
    fontSize: 15,
    fontWeight: '700',
    paddingVertical: 12,
    borderRadius: 8,
    overflow: 'hidden',
  },
  feedbackBtnNo: {backgroundColor: '#27ae60'},
  feedbackThanks: {fontSize: 15, color: '#27ae60', textAlign: 'center', padding: 16},
});
