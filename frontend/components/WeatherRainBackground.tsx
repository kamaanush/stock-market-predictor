"use client";

import {
    useEffect,
    useState,
} from "react";

import styles from "./WeatherRainBackground.module.css";


type CurrentWeather = {
    precipitation?: number;
    rain?: number;
    showers?: number;
    weather_code?: number;
};


type WeatherResponse = {
    current?:
    CurrentWeather;
};


const DROP_COUNT =
    85;


function isRainWeather(
    weather:
        CurrentWeather
) {

    const precipitation =
        Number(
            weather.precipitation ||
            0
        );


    const rain =
        Number(
            weather.rain ||
            0
        );


    const showers =
        Number(
            weather.showers ||
            0
        );


    const code =
        Number(
            weather.weather_code ||
            0
        );


    const rainCode =
        (
            code >= 51 &&
            code <= 67
        )
        ||
        (
            code >= 80 &&
            code <= 82
        )
        ||
        (
            code >= 95 &&
            code <= 99
        );


    return (
        precipitation >
        0 ||
        rain >
        0 ||
        showers >
        0 ||
        rainCode
    );
}


export default function WeatherRainBackground() {

    const [
        raining,
        setRaining,
    ] = useState(
        false
    );


    useEffect(
        () => {

            let active =
                true;


            let refreshTimer:
                number | null =
                null;

            // ==========================================
            // DEVELOPMENT TEST OVERRIDE
            //
            // Browser console:
            //
            // localStorage.setItem(
            //   "nexus_force_rain",
            //   "1"
            // );
            // location.reload();
            //
            // ==========================================

            const forceRain =
                window.localStorage
                    .getItem(
                        "nexus_force_rain"
                    ) ===
                "1";


            if (
                forceRain
            ) {
                
                setRaining(
                    true
                );

                return () => {
                    active =
                        false;
                };

            }


            if (
                !(
                    "geolocation"
                    in navigator
                )
            ) {

                return;

            }


            navigator.geolocation
                .getCurrentPosition(

                    (
                        position
                    ) => {

                        const latitude =
                            position.coords
                                .latitude;


                        const longitude =
                            position.coords
                                .longitude;


                        async function loadWeather() {

                            try {

                                const url =
                                    "https://api.open-meteo.com/v1/forecast"
                                    +
                                    `?latitude=${encodeURIComponent(
                                        latitude
                                    )}`
                                    +
                                    `&longitude=${encodeURIComponent(
                                        longitude
                                    )}`
                                    +
                                    "&current=precipitation,rain,showers,weather_code"
                                    +
                                    "&timezone=auto";


                                const response =
                                    await fetch(
                                        url,
                                        {
                                            cache:
                                                "no-store",
                                        }
                                    );


                                if (
                                    !response.ok
                                ) {

                                    return;

                                }


                                const data:
                                    WeatherResponse =
                                    await response
                                        .json();


                                if (
                                    !active
                                ) {

                                    return;

                                }


                                setRaining(
                                    isRainWeather(
                                        data.current ||
                                        {}
                                    )
                                );


                            } catch {

                                // Weather effects are visual only.
                                // Never disturb the trading terminal.

                            }

                        }


                        void loadWeather();


                        refreshTimer =
                            window.setInterval(
                                () => {

                                    void loadWeather();

                                },
                                10 *
                                60 *
                                1000
                            );

                    },


                    () => {

                        if (
                            active
                        ) {

                            setRaining(
                                false
                            );

                        }

                    },


                    {
                        enableHighAccuracy:
                            false,

                        timeout:
                            8000,

                        maximumAge:
                            10 *
                            60 *
                            1000,
                    }

                );


            return () => {

                active =
                    false;


                if (
                    refreshTimer !==
                    null
                ) {

                    window.clearInterval(
                        refreshTimer
                    );

                }

            };

        },
        []
    );


    return (

        <div
            className={
                `${styles.rain} ${raining
                    ? styles.rainVisible
                    : styles.rainHidden
                }`
            }

            aria-hidden="true"
        >

            <div
                className={
                    styles.rainGlow
                }
            />


            {Array.from({
                length:
                    DROP_COUNT,
            }).map(
                (
                    _,
                    index
                ) => {

                    const left =
                        (
                            index *
                            37
                        )
                        %
                        100;


                    const duration =
                        0.72
                        +
                        (
                            index %
                            8
                        )
                        *
                        0.07;


                    const delay =
                        -(
                            (
                                index *
                                17
                            )
                            %
                            30
                        )
                        /
                        10;


                    const height =
                        14
                        +
                        (
                            index %
                            7
                        )
                        *
                        4;


                    const opacity =
                        0.18
                        +
                        (
                            index %
                            6
                        )
                        *
                        0.055;


                    return (

                        <span
                            key={
                                index
                            }

                            className={
                                styles.drop
                            }

                            style={{
                                left:
                                    `${left}%`,

                                height:
                                    `${height}px`,

                                opacity,

                                animationDuration:
                                    `${duration}s`,

                                animationDelay:
                                    `${delay}s`,
                            }}
                        />

                    );

                }
            )}

        </div>

    );

}