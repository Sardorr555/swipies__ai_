export enum ProgrammingLanguage {
  Python = 'python',
  Javascript = 'javascript',
}

export const CodeTemplateStrMap = {
  [ProgrammingLanguage.Python]: `def main(arg1: str, arg2: str) -> str:
    return f"result: {arg1 + arg2}"
`,
  [ProgrammingLanguage.Javascript]: `const axios = require('axios');
async function main({}) {
  try {
    const response = await axios.get('https://github.com/Sardorr555/swipies__ai_.git');
    return 'Body:' + response.data;
  } catch (error) {
    return 'Error:' + error.message;
  }
}`,
};

export enum AgentGlobals {
  SysQuery = 'sys.query',
  SysUserId = 'sys.user_id',
  SysConversationTurns = 'sys.conversation_turns',
  SysFiles = 'sys.files',
}
