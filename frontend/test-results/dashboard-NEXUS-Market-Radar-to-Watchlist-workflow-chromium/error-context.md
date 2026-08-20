# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: dashboard.spec.ts >> NEXUS Market Radar to Watchlist workflow
- Location: e2e/dashboard.spec.ts:371:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText('NEXUS MARKET INTELLIGENCE', { exact: true })
Expected: visible
Error: element(s) not found

Call log:
  - Expect "toBeVisible" with timeout 15000ms
  - waiting for getByText('NEXUS MARKET INTELLIGENCE', { exact: true })
  - Protocol error (Runtime.callFunctionOn): Internal server error, session closed.

```

```yaml
- 'heading "Application error: a client-side exception has occurred (see the browser console for more information)." [level=2]'
```

# Test source

```ts
  1301 |                 {
  1302 | 
  1303 |                   symbol:
  1304 |                     "ICICIBANK",
  1305 | 
  1306 |                   last_price:
  1307 |                     1435.25,
  1308 | 
  1309 |                   change_percent:
  1310 |                     1.42,
  1311 |                 }
  1312 |               ),
  1313 |           });
  1314 | 
  1315 | 
  1316 |           return;
  1317 |         }
  1318 | 
  1319 | 
  1320 |         // ==================================================
  1321 |         // FALLBACK
  1322 |         // ==================================================
  1323 | 
  1324 |         console.log(
  1325 |           "[PLAYWRIGHT] Unhandled API:",
  1326 |           method,
  1327 |           path
  1328 |         );
  1329 | 
  1330 | 
  1331 |         await route.fulfill({
  1332 |           status:
  1333 |             200,
  1334 | 
  1335 |           contentType:
  1336 |             "application/json",
  1337 | 
  1338 |           body:
  1339 |             JSON.stringify(
  1340 |               {}
  1341 |             ),
  1342 |         });
  1343 | 
  1344 |       }
  1345 |     );
  1346 | 
  1347 | 
  1348 |     // ==================================================
  1349 |     // OPEN DASHBOARD
  1350 |     // ==================================================
  1351 | 
  1352 |     await page.goto(
  1353 |       "/dashboard",
  1354 |       {
  1355 |         waitUntil:
  1356 |           "domcontentloaded",
  1357 |       }
  1358 |     );
  1359 | 
  1360 | 
  1361 |     // ==================================================
  1362 |     // VERIFY SIDEBAR
  1363 |     // ==================================================
  1364 | 
  1365 |     const marketRadarNav =
  1366 |       page
  1367 |         .locator(
  1368 |           "aside.sidebar button.nav-item"
  1369 |         )
  1370 |         .filter({
  1371 |           hasText:
  1372 |             "MARKET RADAR",
  1373 |         });
  1374 | 
  1375 | 
  1376 |     await expect(
  1377 |       marketRadarNav
  1378 |     ).toBeVisible({
  1379 |       timeout:
  1380 |         15_000,
  1381 |     });
  1382 | 
  1383 | 
  1384 |     // ==================================================
  1385 |     // OPEN MARKET RADAR
  1386 |     // ==================================================
  1387 | 
  1388 |     await marketRadarNav.click();
  1389 | 
  1390 | 
  1391 |     // Verify actual Radar component loaded.
  1392 | 
  1393 |     await expect(
  1394 |       page.getByText(
  1395 |         "NEXUS MARKET INTELLIGENCE",
  1396 |         {
  1397 |           exact:
  1398 |             true,
  1399 |         }
  1400 |       )
> 1401 |     ).toBeVisible({
       |       ^ Error: expect(locator).toBeVisible() failed
  1402 |       timeout:
  1403 |         15_000,
  1404 |     });
  1405 | 
  1406 | 
  1407 |     // ==================================================
  1408 |     // OPEN NSE UNIVERSE / ALL STOCKS
  1409 |     // ==================================================
  1410 | 
  1411 |     const universeTab =
  1412 |       page
  1413 |         .locator(
  1414 |           "button"
  1415 |         )
  1416 |         .filter({
  1417 |           hasText:
  1418 |             /NSE UNIVERSE|ALL STOCKS/i,
  1419 |         })
  1420 |         .first();
  1421 | 
  1422 | 
  1423 |     await expect(
  1424 |       universeTab
  1425 |     ).toBeVisible({
  1426 |       timeout:
  1427 |         15_000,
  1428 |     });
  1429 | 
  1430 | 
  1431 |     await universeTab.click();
  1432 | 
  1433 | 
  1434 |     // ==================================================
  1435 |     // FIND UNIVERSE SEARCH
  1436 |     // ==================================================
  1437 | 
  1438 |     const universeSearch =
  1439 |       page.getByPlaceholder(
  1440 |         /Search symbol or company/i
  1441 |       );
  1442 | 
  1443 | 
  1444 |     await expect(
  1445 |       universeSearch
  1446 |     ).toBeVisible({
  1447 |       timeout:
  1448 |         10_000,
  1449 |     });
  1450 | 
  1451 | 
  1452 |     // ==================================================
  1453 |     // SEARCH ICICI
  1454 |     // ==================================================
  1455 | 
  1456 |     await universeSearch.fill(
  1457 |       "ICICIBANK"
  1458 |     );
  1459 | 
  1460 | 
  1461 |     const iciciUniverseRow =
  1462 |       page
  1463 |         .locator(
  1464 |           "tbody tr"
  1465 |         )
  1466 |         .filter({
  1467 |           hasText:
  1468 |             "ICICIBANK",
  1469 |         })
  1470 |         .first();
  1471 | 
  1472 | 
  1473 |     await expect(
  1474 |       iciciUniverseRow
  1475 |     ).toBeVisible({
  1476 |       timeout:
  1477 |         15_000,
  1478 |     });
  1479 | 
  1480 | 
  1481 |     await expect(
  1482 |       iciciUniverseRow
  1483 |     ).toContainText(
  1484 |       "ICICI Bank"
  1485 |     );
  1486 | 
  1487 | 
  1488 |     // ==================================================
  1489 |     // FIND WATCH BUTTON
  1490 |     // ==================================================
  1491 | 
  1492 |     const addButton =
  1493 |       iciciUniverseRow
  1494 |         .getByRole(
  1495 |           "button",
  1496 |           {
  1497 |             name:
  1498 |               /\+ WATCH|ADDING/i,
  1499 |           }
  1500 |         );
  1501 | 
```