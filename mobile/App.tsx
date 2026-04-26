import React from 'react';
import {NavigationContainer} from '@react-navigation/native';
import {createStackNavigator} from '@react-navigation/stack';
import {SafeAreaProvider} from 'react-native-safe-area-context';

import InboxScreen from './src/screens/InboxScreen';
import EmailDetailScreen from './src/screens/EmailDetailScreen';

export type RootStackParamList = {
  Inbox: undefined;
  EmailDetail: {emailId: string};
};

const Stack = createStackNavigator<RootStackParamList>();

export default function App() {
  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator
          screenOptions={{
            headerStyle: {backgroundColor: '#1a1a2e'},
            headerTintColor: '#ffffff',
            headerTitleStyle: {fontSize: 20, fontWeight: 'bold'},
          }}>
          <Stack.Screen name="Inbox" component={InboxScreen} options={{title: 'Your Inbox'}} />
          <Stack.Screen
            name="EmailDetail"
            component={EmailDetailScreen}
            options={{title: 'Email Details'}}
          />
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
