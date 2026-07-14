import { css } from 'lit';

export const commonStyle = css`
    :host {
        color: var(--primary-text-color);
        background: var(--lovelace-background, var(--primary-background-color));
        /* Establish a positioning context so the dialog can use position: absolute
           instead of the default position: fixed (which covers the full viewport
           and centers on the viewport, not on the Current Tasks card). */
        position: relative;
    }

    .header {
        background-color: var(--app-header-background-color);
        color: var(--app-header-text-color, white);
        border-bottom: var(--app-header-border-bottom, none);
    }

    .toolbar {
        height: var(--header-height);
        display: flex;
        align-items: center;
        font-size: 20px;
        padding: 0 16px;
        font-weight: 400;
        box-sizing: border-box;
    }

    .main-title {
        margin: 0 0 0 24px;
        line-height: 20px;
        flex-grow: 1;
    }

    .version {
        font-size: 14px;
        font-weight: 500;
        color: rgba(var(--rgb-text-primary-color), 0.9);
    }

    .view {
        height: calc(100vh - 65px);
        display: flex;
        align-content: start;
        justify-content: center;
        flex-wrap: wrap;
        align-items: flex-start;
        /* Give breathing room between the toolbar and the tasks card */
        padding-top: 32px;
    }

    ha-card {
        display: block;
        margin: 5px;
    }

    .card-current {
        width: 100%;
        max-width: 100%;
    }

    ha-expansion-panel {
        --input-fill-color: none;
    }

    .form-row {
        display: flex;
        justify-content: center;
        gap: 8px;
        flex-wrap: wrap;
    }

    .form-field,
    ha-textfield,
    ha-select,
    ha-icon-picker {
        text-align: right;
        min-width: 265px;
    }

    .extras-panel{
        margin-bottom: 14px;
    }

    .filler {
        flex-grow: 1;
    }

    .break {
        flex-basis: 100%;
        height: 0;
    }

    @media (max-width: 600px) {
        .form-row {
            flex-direction: column; /* Stack fields vertically */
        }

        .form-field {
            width: 100%; /* Full width */
        }

        ha-textfield,
        ha-select,
        ha-icon-picker {
            width: 100%;
            box-sizing: border-box;
        }
    }

    .task-list {
        list-style: none;
        padding: 0;
        margin: 0;
    }

    .task-item {
        display: flex;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        gap: 1rem;
        padding: 0.5rem 0;
        border-bottom: 1px solid var(--divider-color);
    }

    .task-header {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .task-content {
        flex: 1;
    }

    .due-soon {
        color: var(--error-color, red);
        font-weight: bold;
    }

    .warning {
        --mdc-theme-primary: var(--error-color);
        color: var(--primary-text-color);
    }

    .add-task-button {
        margin-right: 16px;
        --mdc-theme-primary: var(--primary-color);
    }

    .empty-state {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 48px 16px;
        text-align: center;
    }

    .empty-icon {
        --mdc-icon-size: 64px;
        color: var(--secondary-text-color);
        margin-bottom: 16px;
    }

    .empty-title {
        font-size: 20px;
        font-weight: 500;
        margin: 0 0 8px 0;
        color: var(--primary-text-color);
    }

    .empty-description {
        font-size: 14px;
        margin: 0 0 24px 0;
        color: var(--secondary-text-color);
    }

    .add-task-button-empty {
        --mdc-theme-primary: var(--primary-color);
    }

    ha-dialog {
        --mdc-dialog-min-width: 600px;
        --mdc-dialog-max-width: 90vw;
        /* Override MWC's default position: fixed (covers viewport, center = viewport center)
           with position: absolute (covers the :host, center = host center = Current Tasks card
           center). The ::part(scrim) override below handles the MWC's internal shadow DOM
           scrim element which defaults to position: fixed. */
        position: absolute !important;
        inset: 0 !important;
    }

    /* Target the scrim inside MWC dialog's shadow DOM.
       This overrides the default position: fixed (viewport-relative)
       with position: absolute (host-relative). Combined with the
       :host { position: relative; } above, the scrim fills the host
       element's box, so the dialog surface centers on the host =
       the Current Tasks card. */
    ha-dialog::part(scrim) {
        position: absolute !important;
        inset: 0 !important;
    }

    @media (max-width: 600px) {
        ha-dialog {
        --mdc-dialog-min-width: auto;
        }
    }
`;