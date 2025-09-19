# Open file in read mode
with open("demo.txt", "r") as file:
    # Read all content
    content = file.read()

# Print the content
print(content)


with open("output.txt", "w") as file:
    file.write(content)
    