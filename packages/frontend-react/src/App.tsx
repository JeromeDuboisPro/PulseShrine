import AuthWrapper from './components/AuthWrapper';
import { PulseApp } from './components/PulseApp';

const App = () => {
  return (
    <AuthWrapper>
      <PulseApp />
    </AuthWrapper>
  );
};

export default App;