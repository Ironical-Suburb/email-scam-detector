import React, {useEffect, useState, useCallback} from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import {useNavigation} from '@react-navigation/native';
import type {StackNavigationProp} from '@react-navigation/stack';
import type {RootStackParamList} from '../../App';
import {api} from '../api';

type Nav = StackNavigationProp<RootStackParamList, 'Inbox'>;

type EmailSummary = {
  id: string;
  subject: string;
  from: string;
  risk_label: 'flagged' | 'review' | 'clean';
  risk_score: number;
  scam_type: string | null;
};

const RISK_COLORS = {
  flagged: '#e74c3c',
  review: '#f39c12',
  clean: '#27ae60',
};

const RISK_LABELS = {
  flagged: 'SCAM',
  review: 'REVIEW',
  clean: 'OK',
};

export default function InboxScreen() {
  const navigation = useNavigation<Nav>();
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await api.getInbox();
      setEmails(data);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = () => {
    setRefreshing(true);
    load();
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#e74c3c" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <FlatList
        data={emails}
        keyExtractor={item => item.id}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        renderItem={({item}) => (
          <TouchableOpacity
            style={styles.row}
            onPress={() => navigation.navigate('EmailDetail', {emailId: item.id})}>
            <View style={styles.rowLeft}>
              <Text style={styles.from} numberOfLines={1}>
                {item.from}
              </Text>
              <Text style={styles.subject} numberOfLines={1}>
                {item.subject}
              </Text>
            </View>
            <View style={[styles.badge, {backgroundColor: RISK_COLORS[item.risk_label]}]}>
              <Text style={styles.badgeText}>{RISK_LABELS[item.risk_label]}</Text>
            </View>
          </TouchableOpacity>
        )}
        ItemSeparatorComponent={() => <View style={styles.separator} />}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {flex: 1, backgroundColor: '#f5f5f5'},
  center: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  rowLeft: {flex: 1, marginRight: 12},
  from: {fontSize: 16, fontWeight: '600', color: '#1a1a2e'},
  subject: {fontSize: 14, color: '#555', marginTop: 2},
  badge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    minWidth: 60,
    alignItems: 'center',
  },
  badgeText: {color: '#fff', fontWeight: '700', fontSize: 12},
  separator: {height: 1, backgroundColor: '#e0e0e0'},
});
