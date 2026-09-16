import FloatingChatWidget from '@/components/floating-chat-widget';

const ChatWidget = () => {
  return (
    <div
      style={{
        background: 'transparent',
        margin: 0,
        padding: 0,
        width: '100%',
        height: '100%',
      }}
    >
      <style>{`
        html, body { 
          background: transparent !important; 
          margin: 0; 
          padding: 0; 
          width: 100%;
          height: 100vh;
          height: 100dvh;
          overscroll-behavior-y: contain;
          -webkit-overflow-scrolling: touch;
        }
        #root {
          background: transparent !important;
          width: 100%;
          height: 100%;
        }
      `}</style>
      <FloatingChatWidget />
    </div>
  );
};

export default ChatWidget;
