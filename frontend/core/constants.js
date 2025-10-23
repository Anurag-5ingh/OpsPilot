(function(){
  window.Core = window.Core || {};
  const Constants = {
    AppName: 'OpsPilot',
    Routes: {
      SSH_LIST: '/ssh/list',
      SSH_SAVE: '/ssh/save',
      SSH_DELETE: (id) => `/ssh/delete/${id}`,
      SSH_TEST: '/ssh/test'
    },
    Events: {
      READY: 'core:ready',
      PROFILE_LIST_UPDATED: 'profiles:list:updated'
    },
    StorageKeys: {
      Profiles: 'ops_profiles'
    }
  };
  window.Core.constants = Constants;
})();
