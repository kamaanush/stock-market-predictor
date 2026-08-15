"use client";

import { useEffect, useState } from "react";
import styles from "./SettingsPanel.module.css";

type HealthResponse = {
  status: string;
  market_mode: string;
  smartapi_configured: boolean;
  market_warning: string | null;
};

type SettingsPanelProps = {
  apiBase: string;
};

export default function SettingsPanel({
  apiBase,
}: SettingsPanelProps) {
  const [health, setHealth] =
    useState<HealthResponse | null>(null);

  const [loading, setLoading] =
    useState(false);

  const [error, setError] =
    useState("");

  const [
    defaultTimeframe,
    setDefaultTimeframe,
  ] = useState<
    "1m" | "5m" | "15m"
  >("5m");

  const [
    minimumConfidence,
    setMinimumConfidence,
  ] = useState(60);

  const [
    backtestDays,
    setBacktestDays,
  ] = useState(10);

  const [
    alertDelivery,
    setAlertDelivery,
  ] = useState<
    "BROWSER" |
    "TELEGRAM" |
    "BOTH"
  >("BROWSER");

  const [
    savedMessage,
    setSavedMessage,
  ] = useState("");

  async function loadHealth() {
    setLoading(true);
    setError("");

    try {
      const response =
        await fetch(
          `${apiBase}/api/health`,
          {
            credentials:
              "include",
          }
        );

      const body =
        (await response
          .json()
          .catch(
            () => ({})
          )) as Partial<HealthResponse>;

      if (!response.ok) {
        throw new Error(
          "Could not load backend health"
        );
      }

      setHealth({
        status:
          body.status ||
          "unknown",

        market_mode:
          body.market_mode ||
          "unknown",

        smartapi_configured:
          body.smartapi_configured ===
          true,

        market_warning:
          body.market_warning ||
          "",
      });
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Could not load settings status"
      );
    } finally {
      setLoading(false);
    }
  }

  function savePreferences() {
    localStorage.setItem(
      "nexus_default_timeframe",
      defaultTimeframe
    );

    localStorage.setItem(
      "nexus_minimum_confidence",
      String(
        minimumConfidence
      )
    );

    localStorage.setItem(
      "nexus_backtest_days",
      String(
        backtestDays
      )
    );

    localStorage.setItem(
      "nexus_alert_delivery",
      alertDelivery
    );

    setSavedMessage(
      "Preferences saved successfully"
    );

    window.setTimeout(
      () => {
        setSavedMessage("");
      },
      2500
    );
  }

  useEffect(() => {
    const timeframe =
      localStorage.getItem(
        "nexus_default_timeframe"
      );

    const confidence =
      localStorage.getItem(
        "nexus_minimum_confidence"
      );

    const days =
      localStorage.getItem(
        "nexus_backtest_days"
      );

    const delivery =
      localStorage.getItem(
        "nexus_alert_delivery"
      );

    if (
      timeframe === "1m" ||
      timeframe === "5m" ||
      timeframe === "15m"
    ) {
      setDefaultTimeframe(
        timeframe
      );
    }

    if (confidence) {
      setMinimumConfidence(
        Number(
          confidence
        )
      );
    }

    if (days) {
      setBacktestDays(
        Number(
          days
        )
      );
    }

    if (
      delivery ===
        "BROWSER" ||
      delivery ===
        "TELEGRAM" ||
      delivery ===
        "BOTH"
    ) {
      setAlertDelivery(
        delivery
      );
    }
  }, []);

  useEffect(() => {
    void loadHealth();
  }, []);

  return (
    <section
      id="settings-section"
      className={
        styles.shell
      }
    >
      <header
        className={
          styles.hero
        }
      >
        <div>
          <span
            className={
              styles.kicker
            }
          >
            SYSTEM PREFERENCES
          </span>

          <h1>
            Settings & Runtime
            Control
          </h1>

          <p>
            Review backend
            connectivity,
            market-data mode and
            application defaults
            without exposing
            credentials or secrets.
          </p>
        </div>

        <button
          type="button"
          className={
            styles.refreshButton
          }
          onClick={() =>
            void loadHealth()
          }
          disabled={loading}
        >
          {loading
            ? "CHECKING…"
            : "REFRESH STATUS"}
        </button>
      </header>

      {error && (
        <div
          className={
            styles.errorBanner
          }
        >
          {error}
        </div>
      )}

      <div
        className={
          styles.metricGrid
        }
      >
        <Metric
          label="BACKEND"
          value={
            health?.status
              ?.toUpperCase() ||
            "—"
          }
          hint="FastAPI runtime"
          tone={
            health?.status ===
            "ok"
              ? "green"
              : "amber"
          }
        />

        <Metric
          label="MARKET MODE"
          value={
            health?.market_mode
              ?.toUpperCase() ||
            "—"
          }
          hint="Current data provider"
          tone={
            health
              ?.market_mode ===
            "smartapi"
              ? "cyan"
              : "violet"
          }
        />

        <Metric
          label="SMARTAPI"
          value={
            health
              ?.smartapi_configured
              ? "CONFIGURED"
              : "NOT CONFIGURED"
          }
          hint="Credential availability"
          tone={
            health
              ?.smartapi_configured
              ? "green"
              : "red"
          }
        />

        <Metric
          label="MARKET WARNING"
          value={
            health
              ?.market_warning
              ? "ATTENTION"
              : "NONE"
          }
          hint={
            health
              ?.market_warning ||
            "No warning reported"
          }
          tone={
            health
              ?.market_warning
              ? "amber"
              : "cyan"
          }
        />
      </div>

      <div
        className={
          styles.mainGrid
        }
      >
        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.panelHeader
            }
          >
            <div>
              <span
                className={
                  styles.kicker
                }
              >
                DATA ENGINE
              </span>

              <h2>
                Market
                connectivity
              </h2>
            </div>
          </div>

          <div
            className={
              styles.statusList
            }
          >
            <StatusRow
              label="Backend API"
              value={
                health?.status ===
                "ok"
                  ? "ONLINE"
                  : "UNKNOWN"
              }
              active={
                health?.status ===
                "ok"
              }
            />

            <StatusRow
              label="Market provider"
              value={
                health
                  ?.market_mode
                  ?.toUpperCase() ||
                "UNKNOWN"
              }
              active={
                health
                  ?.market_mode ===
                "smartapi"
              }
            />

            <StatusRow
              label="SmartAPI credentials"
              value={
                health
                  ?.smartapi_configured
                  ? "READY"
                  : "MISSING"
              }
              active={
                health
                  ?.smartapi_configured ===
                true
              }
            />

            <StatusRow
              label="Fallback mode"
              value={
                health
                  ?.market_mode ===
                "demo"
                  ? "ACTIVE"
                  : "STANDBY"
              }
              active={
                health
                  ?.market_mode ===
                "demo"
              }
            />
          </div>

          <div
            className={
              styles.infoBox
            }
          >
            <span>
              SECURITY NOTE
            </span>

            <p>
              API keys, PINs,
              TOTP secrets,
              session secrets and
              Telegram tokens are
              intentionally hidden
              from this interface.
            </p>
          </div>
        </section>

        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.panelHeader
            }
          >
            <div>
              <span
                className={
                  styles.kicker
                }
              >
                SCANNER DEFAULTS
              </span>

              <h2>
                Analysis
                preferences
              </h2>
            </div>
          </div>

          <div
            className={
              styles.formGrid
            }
          >
            <label>
              <span>
                DEFAULT TIMEFRAME
              </span>

              <select
                value={
                  defaultTimeframe
                }
                onChange={(
                  event
                ) =>
                  setDefaultTimeframe(
                    event.target
                      .value as
                      | "1m"
                      | "5m"
                      | "15m"
                  )
                }
              >
                <option value="1m">
                  1 minute
                </option>

                <option value="5m">
                  5 minutes
                </option>

                <option value="15m">
                  15 minutes
                </option>
              </select>
            </label>

            <label>
              <span>
                MIN CONFIDENCE
              </span>

              <input
                type="number"
                min="1"
                max="100"
                value={
                  minimumConfidence
                }
                onChange={(
                  event
                ) =>
                  setMinimumConfidence(
                    Number(
                      event.target
                        .value
                    )
                  )
                }
              />
            </label>

            <label>
              <span>
                BACKTEST DAYS
              </span>

              <input
                type="number"
                min="1"
                max="365"
                value={
                  backtestDays
                }
                onChange={(
                  event
                ) =>
                  setBacktestDays(
                    Number(
                      event.target
                        .value
                    )
                  )
                }
              />
            </label>

            <label>
              <span>
                ALERT DELIVERY
              </span>

              <select
                value={
                  alertDelivery
                }
                onChange={(
                  event
                ) =>
                  setAlertDelivery(
                    event.target
                      .value as
                      | "BROWSER"
                      | "TELEGRAM"
                      | "BOTH"
                  )
                }
              >
                <option
                  value="BROWSER"
                >
                  Browser
                </option>

                <option
                  value="TELEGRAM"
                >
                  Telegram
                </option>

                <option
                  value="BOTH"
                >
                  Browser +
                  Telegram
                </option>
              </select>
            </label>
          </div>

          <div
            className={
              styles.saveArea
            }
          >
            <button
              type="button"
              className={
                styles.saveButton
              }
              onClick={
                savePreferences
              }
            >
              SAVE PREFERENCES
            </button>

            {savedMessage && (
              <span
                className={
                  styles.savedMessage
                }
              >
                ✓ {savedMessage}
              </span>
            )}
          </div>

          <div
            className={
              styles.preferenceNote
            }
          >
            <span>
              LOCAL UI DEFAULTS
            </span>

            <p>
              These preferences are
              stored in browser
              localStorage and remain
              available after page
              refresh.
            </p>
          </div>
        </section>
      </div>

      <div
        className={
          styles.bottomGrid
        }
      >
        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.panelHeader
            }
          >
            <div>
              <span
                className={
                  styles.kicker
                }
              >
                APPLICATION
              </span>

              <h2>
                Runtime profile
              </h2>
            </div>
          </div>

          <div
            className={
              styles.profileGrid
            }
          >
            <Profile
              label="Frontend"
              value="Next.js"
            />

            <Profile
              label="Backend"
              value="FastAPI"
            />

            <Profile
              label="Auth"
              value="Session cookie"
            />

            <Profile
              label="Market"
              value={
                health
                  ?.market_mode
                  ?.toUpperCase() ||
                "—"
              }
            />
          </div>
        </section>

        <section
          className={
            styles.card
          }
        >
          <div
            className={
              styles.panelHeader
            }
          >
            <div>
              <span
                className={
                  styles.kicker
                }
              >
                CONNECTION SUMMARY
              </span>

              <h2>
                Current environment
              </h2>
            </div>
          </div>

          <div
            className={
              styles.connectionSummary
            }
          >
            <div
              className={
                health?.status ===
                "ok"
                  ? styles.summaryOrbOnline
                  : styles.summaryOrbOffline
              }
            >
              <span />
              <span />

              <strong>
                {health?.status ===
                "ok"
                  ? "ONLINE"
                  : "CHECK"}
              </strong>
            </div>

            <div>
              <strong>
                {health
                  ?.market_mode ===
                "smartapi"
                  ? "Live SmartAPI mode"
                  : "Demo market mode"}
              </strong>

              <p>
                {health
                  ?.smartapi_configured
                  ? "SmartAPI configuration is available to the backend."
                  : "SmartAPI is not configured, so the application is using demo/fallback market data."}
              </p>
            </div>
          </div>
        </section>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string;
  hint: string;
  tone:
    | "cyan"
    | "green"
    | "red"
    | "violet"
    | "amber";
}) {
  return (
    <div
      className={`${styles.metric} ${
        styles[
          `metric_${tone}`
        ]
      }`}
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

      <small>
        {hint}
      </small>
    </div>
  );
}

function StatusRow({
  label,
  value,
  active,
}: {
  label: string;
  value: string;
  active: boolean;
}) {
  return (
    <div
      className={
        styles.statusRow
      }
    >
      <div>
        <strong>
          {label}
        </strong>
      </div>

      <span
        className={
          active
            ? styles.statusOn
            : styles.statusOff
        }
      >
        <i />
        {value}
      </span>
    </div>
  );
}

function Profile({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      className={
        styles.profile
      }
    >
      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>
    </div>
  );
}