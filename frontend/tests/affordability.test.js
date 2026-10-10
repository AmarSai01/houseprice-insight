import assert from "node:assert/strict";
import test from "node:test";
import {
  computeEmi,
  computeEmiShareOfIncome,
  computeLoanAmount,
  computeMonthlyRate,
  roundCurrency,
  validateAffordabilityInputs,
} from "../src/services/affordability.js";

function expectedEmi(principal, annualRatePercent, tenureYears) {
  const n = tenureYears * 12;
  if (annualRatePercent === 0) return principal / n;
  const r = annualRatePercent / 12 / 100;
  const compound = (1 + r) ** n;
  return (principal * r * compound) / (compound - 1);
}

test("computeMonthlyRate converts annual percentage to decimal monthly rate", () => {
  assert.equal(computeMonthlyRate(12), 0.01);
  assert.equal(computeMonthlyRate(8.5), 8.5 / 12 / 100);
});

test("standard EMI matches amortization formula", () => {
  const principal = 1_000_000;
  const rate = 8.5;
  const years = 20;
  const emi = computeEmi(principal, rate, years);
  assert.ok(Math.abs(emi - expectedEmi(principal, rate, years)) < 1e-6);
});

test("zero-interest EMI equals principal divided by months", () => {
  const principal = 120_000;
  const years = 10;
  assert.equal(computeEmi(principal, 0, years), 1000);
});

test("computeLoanAmount subtracts down payment from property price", () => {
  assert.equal(computeLoanAmount(5_000_000, 500_000), 4_500_000);
});

test("validateAffordabilityInputs computes totals from EMI", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "100000",
    annualRate: "8.5",
    tenureYears: "20",
    monthlyIncome: "",
  });
  assert.equal(evaluation.valid, true);
  const { result } = evaluation;
  const emiRaw = expectedEmi(900_000, 8.5, 20);
  assert.equal(result.emi, roundCurrency(emiRaw));
  assert.equal(result.loanAmount, 900_000);
  assert.equal(result.totalPayment, roundCurrency(result.emi * 240));
  assert.equal(result.totalInterest, result.totalPayment - result.loanAmount);
});

test("income share is EMI divided by monthly income", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "0",
    annualRate: "0",
    tenureYears: "10",
    monthlyIncome: "50000",
  });
  assert.equal(evaluation.valid, true);
  assert.equal(
    evaluation.result.emiIncomeSharePercent,
    computeEmiShareOfIncome(evaluation.result.emi, 50_000)
  );
});

test("rejects empty and invalid property price", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "",
    downPayment: "0",
    annualRate: "8",
    tenureYears: "20",
  });
  assert.equal(evaluation.valid, false);
  assert.ok(evaluation.errors.propertyPrice);
});

test("rejects negative interest rate", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "100000",
    annualRate: "-1",
    tenureYears: "20",
  });
  assert.equal(evaluation.valid, false);
  assert.ok(evaluation.errors.annualRate);
});

test("rejects down payment equal to property price", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "1000000",
    annualRate: "8",
    tenureYears: "20",
  });
  assert.equal(evaluation.valid, false);
  assert.ok(evaluation.errors.downPayment);
});

test("rejects down payment greater than property price", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "1000001",
    annualRate: "8",
    tenureYears: "20",
  });
  assert.equal(evaluation.valid, false);
  assert.ok(evaluation.errors.downPayment);
});

test("supports decimal interest rates", () => {
  const emi = computeEmi(500_000, 8.75, 15);
  assert.ok(Math.abs(emi - expectedEmi(500_000, 8.75, 15)) < 1e-6);
});

test("rejects excessive loan tenure", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "0",
    annualRate: "8",
    tenureYears: "41",
  });
  assert.equal(evaluation.valid, false);
  assert.ok(evaluation.errors.tenureYears);
});

test("different tenures produce different EMIs", () => {
  const emi10 = computeEmi(1_000_000, 8.5, 10);
  const emi20 = computeEmi(1_000_000, 8.5, 20);
  assert.ok(emi10 > emi20);
});

test("rejects invalid monthly income when provided", () => {
  const evaluation = validateAffordabilityInputs({
    propertyPrice: "1000000",
    downPayment: "0",
    annualRate: "8",
    tenureYears: "20",
    monthlyIncome: "0",
  });
  assert.equal(evaluation.valid, false);
  assert.ok(evaluation.errors.monthlyIncome);
});
