/**
 * Deliberately narrow scope: this project had zero test infrastructure.
 * Rather than pull in the full jest-expo + RN Testing Library stack (a large,
 * separate piece of work), this config targets pure TypeScript logic only -
 * the error-mapping and API-client behavior that fault handling depends on.
 * Component rendering tests are a natural next step once jest-expo is added.
 */
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  testMatch: ["<rootDir>/src/**/*.test.ts"],
  transform: { "^.+\\.tsx?$": ["ts-jest", { tsconfig: "tsconfig.json" }] },
  moduleNameMapper: { "^@/(.*)$": "<rootDir>/src/$1" },
};
