import math

sols_with_two = 2*math.comb(460,97)

sols_with_three = 2*math.comb(460,96)

total_sols = sols_with_two+sols_with_three



#print(sols_with_three/(sols_with_two+sols_with_three))

numerator = 97 * math.comb(460,97) + 96 * math.comb(460,96)
denominator = 460 * (math.comb(460,97) + math.comb(460,96))
print(numerator/denominator)