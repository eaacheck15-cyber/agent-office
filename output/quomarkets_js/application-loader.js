(function () {
  'use strict';

  class ApplicationLoader {
      constructor() {
          this.container = null;
          const loaderTemplate = document.querySelector(ApplicationLoader.QUERY_SELECTOR);
          if (!loaderTemplate) {
              console.warn('Loader template not found. Please add a loader template with the attribute [data-loader-template] before the script tag.');
              return;
          }
          const content = loaderTemplate.content.cloneNode(true);
          this.container = this.createContainer();
          this.container.appendChild(content);
          document.body.appendChild(this.container);
      }
      createContainer() {
          const container = document.createElement('div');
          container.classList.add('application-loader-container');
          container.id = 'application-loader-container';
          const style = document.createElement('style');
          style.innerHTML = `
      .application-loader-container {
        position: fixed;
        inset: 0;
        z-index: 1000;
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: var(--background);
      }
    `;
          container.appendChild(style);
          return container;
      }
      fadeToOpacity(opacity) {
          if (!this.container) {
              return;
          }
          this.container.style.transition = `opacity ${ApplicationLoader.FADE_TIME_MS}ms ease`;
          this.container.style.opacity = `${opacity}`;
      }
      resetAnimation() {
          if (!this.container) {
              return;
          }
          this.container.style.opacity = '1';
          this.container.style.transition = '';
      }
      setHiddenState() {
          if (!this.container) {
              return;
          }
          this.container.style.display = 'none';
          this.resetAnimation();
      }
      setVisibleState() {
          if (!this.container) {
              return;
          }
          this.container.style.display = 'flex';
          this.resetAnimation();
      }
      hide(hasFade = true) {
          if (hasFade) {
              this.fadeToOpacity(0);
              setTimeout(() => this.setHiddenState(), ApplicationLoader.FADE_TIME_MS);
          }
          else {
              this.setHiddenState();
          }
      }
      show(hasFade = true) {
          if (hasFade) {
              this.fadeToOpacity(1);
              setTimeout(() => this.setVisibleState(), ApplicationLoader.FADE_TIME_MS);
          }
          else {
              this.setVisibleState();
          }
      }
  }
  ApplicationLoader.QUERY_SELECTOR = 'template[data-loader-template]';
  ApplicationLoader.FADE_TIME_MS = 300;
  if (!window.ApplicationLoader) {
      window.ApplicationLoader = new ApplicationLoader();
  }

})();
