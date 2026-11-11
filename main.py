from sipl import parse_sipl, SIPLSyntaxError

valid_code = """
begin
    R := 1;
    while Y > 0 do
    begin
        R := R * X;
        Y := Y - 1
    end
end
"""

invalid_code = """
begin
    R = 1
end
"""

print("Check correct code")
try:
    ast_tree = parse_sipl(valid_code)
    print(f"The outer block begins on the line: {ast_tree.span.line}")
    print(f"AST: {ast_tree}")
except SIPLSyntaxError as e:
    print(e)

print("\nError check")
try:
    parse_sipl(invalid_code)
except SIPLSyntaxError as e:
    print(e)