module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'docs',
        'style',
        'refactor',
        'perf',
        'test',
        'chore',
        'ci',
        'build'
      ]
    ],
    'scope-case': [2, 'always', 'kebab-case'],
    'subject-case': [2, 'always', 'sentence-case'],
    'subject-empty': [2, 'never'],
    'subject-max-length': [2, 'always', 72],
    'header-max-length': [2, 'always', 100],
    'body-max-line-length': [2, 'always', 72],
    'footer-max-line-length': [2, 'always', 72]
  },
  prompt: {
    settings: {},
    questions: {
      type: {
        description: 'Select the type of change:',
        enum: {
          feat: { description: 'A new feature', title: 'Features', emoji: '✨' },
          fix: { description: 'A bug fix', title: 'Bug Fixes', emoji: '🐛' },
          docs: { description: 'Documentation only changes', title: 'Documentation', emoji: '📚' },
          style: { description: 'Changes that do not affect the meaning of the code', title: 'Styles', emoji: '💎' },
          refactor: { description: 'A code change that neither fixes a bug nor adds a feature', title: 'Code Refactoring', emoji: '♻️' },
          perf: { description: 'A code change that improves performance', title: 'Performance Improvements', emoji: '⚡' },
          test: { description: 'Adding missing tests or correcting existing tests', title: 'Tests', emoji: '✅' },
          chore: { description: 'Changes to the build process or auxiliary tools', title: 'Chores', emoji: '🔧' },
          ci: { description: 'Changes to CI configuration files and scripts', title: 'Continuous Integration', emoji: '🤖' },
          build: { description: 'Changes that affect the build system or external dependencies', title: 'Build System', emoji: '📦' }
        }
      },
      scope: {
        description: 'Scope of the change (e.g., catalog, document, translation):'
      },
      subject: {
        description: 'Short description (imperative mood, max 72 chars):'
      },
      body: {
        description: 'Longer description (why, not how):'
      },
      isBreaking: {
        description: 'Are there any breaking changes?'
      },
      breakingBody: {
        description: 'Describe the breaking changes:'
      },
      breaking: {
        description: 'Select the breaking change type:'
      },
      isIssueAffected: {
        description: 'Does this change affect any open issues?'
      },
      issuesBody: {
        description: 'Add issue references (e.g., "Closes #123"):'
      }
    }
  }
};